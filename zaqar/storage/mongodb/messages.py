# Copyright (c) 2013 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Implements MongoDB the storage controller for messages.

Field Mappings:
    In order to reduce the disk / memory space used,
    field names will be, most of the time, the first
    letter of their long name.
"""

import datetime
import time

from bson import objectid
from oslo_log import log as logging
from oslo_utils import timeutils
import pymongo.errors
import pymongo.read_preferences

from zaqar.i18n import _
from zaqar import storage
from zaqar.storage import errors
from zaqar.storage.mongodb import utils


LOG = logging.getLogger(__name__)

# NOTE(kgriffs): This value, in seconds, should be at least less than the
# minimum allowed TTL for messages (60 seconds). Make it 45 to allow for
# some fudge room.
MAX_RETRY_POST_DURATION = 45

# NOTE(kgriffs): It is extremely unlikely that all workers would somehow hang
# for more than 5 seconds, without a single one being able to succeed in
# posting some messages and incrementing the counter, thus allowing the other
# producers to succeed in turn.
COUNTER_STALL_WINDOW = 5

# For hinting
ID_INDEX_FIELDS = [('_id', 1)]

# For removing expired messages
TTL_INDEX_FIELDS = [
    ('e', 1),
]

# NOTE(cpp-cabrera): to unify use of project/queue across mongodb
# storage impls.
PROJ_QUEUE = utils.PROJ_QUEUE_KEY

# NOTE(kgriffs): This index is for listing messages, usually
# filtering out claimed ones.
ACTIVE_INDEX_FIELDS = [
    (PROJ_QUEUE, 1),  # Project will be unique, so put first
    ('k', 1),  # Used for sorting and paging, must come before range queries
    ('c.e', 1),  # Used for filtering out claimed messages

    # NOTE(kgriffs): We do not include 'u' and 'tx' here on
    # purpose. It was found experimentally that adding 'u' did
    # not improve performance, and so it was left out in order
    # to reduce index size and make updating the index
    # faster. When 'tx' was added, it was assumed that it would
    # follow a similar performance pattern to 'u', since by
    # the time you traverse the index down past the fields
    # listed above, there is very little left to scan, esp.
    # considering all queries are limited (limit=) to a fairly
    # small number.
    #
    # TODO(kgriffs): The extrapolation wrt 'tx' needs to be
    # proven empirically.
]

# For counting
COUNTING_INDEX_FIELDS = [
    (PROJ_QUEUE, 1),  # Project will be unique, so put first
    ('c.e', 1),  # Used for filtering out claimed messages
]

# Index used for claims
CLAIMED_INDEX_FIELDS = [
    (PROJ_QUEUE, 1),
    ('c.id', 1),
    ('k', 1),
    ('c.e', 1),
]

# This index is meant to be used as a shard-key and to ensure
# uniqueness for markers.
#
# As for other compound indexes, order matters. The marker `k`
# gives enough cardinality to ensure chunks are evenly distributed,
# whereas the `p_q` field helps keeping chunks from the same project
# and queue together.
#
# In a sharded environment, uniqueness of this index is still guaranteed
# because it's used as a shard key.
MARKER_INDEX_FIELDS = [
    ('k', 1),
    (PROJ_QUEUE, 1),
]

TRANSACTION_INDEX_FIELDS = [
    ('tx', 1),
]


class MessageController(storage.Message):
    """Implements message resource operations using MongoDB.

    Messages are scoped by project + queue.

    ::

        Messages:
            Name                Field
            -------------------------
            scope            ->   p_q
            ttl              ->     t
            expires          ->     e
            marker           ->     k
            body             ->     b
            claim            ->     c
            client uuid      ->     u
            transaction      ->    tx
    """

    def __init__(self, *args, **kwargs):
        super(MessageController, self).__init__(*args, **kwargs)

        # Cache for convenience and performance
        self._num_partitions = self.driver.mongodb_conf.partitions
        self._queue_ctrl = self.driver.queue_controller
        self._retry_range = range(self.driver.mongodb_conf.max_attempts)

        # Create a list of 'messages' collections, one for each database
        # partition, ordered by partition number.
        #
        # NOTE(kgriffs): Order matters, since it is used to lookup the
        # collection by partition number. For example, self._collections[2]
        # would provide access to zaqar_p2.messages (partition numbers are
        # zero-based).
        self._collections = [db.messages
                             for db in self.driver.message_databases]

        # Ensure indexes are initialized before any queries are performed
        for collection in self._collections:
            self._ensure_indexes(collection)

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    def _ensure_indexes(self, collection):
        """Ensures that all indexes are created."""

        collection.ensure_index(TTL_INDEX_FIELDS,
                                name='ttl',
                                expireAfterSeconds=0,
                                background=True)

        collection.ensure_index(ACTIVE_INDEX_FIELDS,
                                name='active',
                                background=True)

        collection.ensure_index(CLAIMED_INDEX_FIELDS,
                                name='claimed',
                                background=True)

        collection.ensure_index(COUNTING_INDEX_FIELDS,
                                name='counting',
                                background=True)

        collection.ensure_index(MARKER_INDEX_FIELDS,
                                name='queue_marker',
                                background=True)

        collection.ensure_index(TRANSACTION_INDEX_FIELDS,
                                name='transaction',
                                background=True)

    def _collection(self, queue_name, project=None):
        """Get a partitioned collection instance."""
        return self._collections[utils.get_partition(self._num_partitions,
                                                     queue_name, project)]

    def _backoff_sleep(self, attempt):
        """Sleep between retries using a jitter algorithm.

        Mitigates thrashing between multiple parallel requests, and
        creates backpressure on clients to slow down the rate
        at which they submit requests.

        :param attempt: current attempt number, zero-based
        """
        conf = self.driver.mongodb_conf
        seconds = utils.calculate_backoff(attempt, conf.max_attempts,
                                          conf.max_retry_sleep,
                                          conf.max_retry_jitter)

        time.sleep(seconds)

    def _purge_queue(self, queue_name, project=None):
        """Removes all messages from the queue.

        Warning: Only use this when deleting the queue; otherwise
        you can cause a side-effect of reseting the marker counter
        which can cause clients to miss tons of messages.

        If the queue does not exist, this method fails silently.

        :param queue_name: name of the queue to purge
        :param project: ID of the project to which the queue belongs
        """
        scope = utils.scope_queue_name(queue_name, project)
        collection = self._collection(queue_name, project)
        collection.delete_many({PROJ_QUEUE: scope})

    def _list(self, queue_name, project=None, marker=None,
              echo=False, client_uuid=None, projection=None,
              include_claimed=False, sort=1, limit=None):
        """Message document listing helper.

        :param queue_name: Name of the queue to list
        :param project: (Default None) Project `queue_name` belongs to. If
            not specified, queries the "global" namespace/project.
        :param marker: (Default None) Message marker from which to start
            iterating. If not specified, starts with the first message
            available in the queue.
        :param echo: (Default False) Whether to return messages that match
            client_uuid
        :param client_uuid: (Default None) UUID for the client that
            originated this request
        :param projection: (Default None) a list of field names that should be
            returned in the result set or a dict specifying the fields to
            include or exclude
        :param include_claimed: (Default False) Whether to include
            claimed messages, not just active ones
        :param sort: (Default 1) Sort order for the listing. Pass 1 for
            ascending (oldest message first), or -1 for descending (newest
            message first).
        :param limit: (Default None) The maximum number of messages
            to list. The results may include fewer messages than the
            requested `limit` if not enough are available. If limit is
            not specified

        :returns: Generator yielding up to `limit` messages.
        """

        if sort not in (1, -1):
            raise ValueError(u'sort must be either 1 (ascending) '
                             u'or -1 (descending)')

        now = timeutils.utcnow_ts()

        query = {
            # Messages must belong to this queue and project.
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),

            # NOTE(kgriffs): Messages must be finalized (i.e., must not
            # be part of an unfinalized transaction).
            #
            # See also the note wrt 'tx' within the definition
            # of ACTIVE_INDEX_FIELDS.
            'tx': None,
        }

        if not echo:
            query['u'] = {'$ne': client_uuid}

        if marker is not None:
            query['k'] = {'$gt': marker}

        collection = self._collection(queue_name, project)

        if not include_claimed:
            # Only include messages that are not part of
            # any claim, or are part of an expired claim.
            query['c.e'] = {'$lte': now}

        # Construct the request
        cursor = collection.find(query,
                                 projection=projection,
                                 sort=[('k', sort)])

        if limit is not None:
            cursor.limit(limit)

        # NOTE(flaper87): Suggest the index to use for this query to
        # ensure the most performant one is chosen.
        return cursor.hint(ACTIVE_INDEX_FIELDS)

    # ----------------------------------------------------------------------
    # "Friends" interface
    # ----------------------------------------------------------------------

    def _count(self, queue_name, project=None, include_claimed=False):
        """Return total number of messages in a queue.

        This method is designed to very quickly count the number
        of messages in a given queue. Expired messages are not
        counted, of course. If the queue does not exist, the
        count will always be 0.

        Note: Some expired messages may be included in the count if
            they haven't been GC'd yet. This is done for performance.
        """
        query = {
            # Messages must belong to this queue and project.
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),

            # NOTE(kgriffs): Messages must be finalized (i.e., must not
            # be part of an unfinalized transaction).
            #
            # See also the note wrt 'tx' within the definition
            # of ACTIVE_INDEX_FIELDS.
            'tx': None,
        }

        if not include_claimed:
            # Exclude messages that are claimed
            query['c.e'] = {'$lte': timeutils.utcnow_ts()}

        collection = self._collection(queue_name, project)
        return collection.count(filter=query, hint=COUNTING_INDEX_FIELDS)

    def _active(self, queue_name, marker=None, echo=False,
                client_uuid=None, projection=None, project=None,
                limit=None):

        return self._list(queue_name, project=project, marker=marker,
                          echo=echo, client_uuid=client_uuid,
                          projection=projection, include_claimed=False,
                          limit=limit)

    def _claimed(self, queue_name, claim_id,
                 expires=None, limit=None, project=None):

        if claim_id is None:
            claim_id = {'$ne': None}

        query = {
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
            'c.id': claim_id,
            'c.e': {'$gt': expires or timeutils.utcnow_ts()},
        }

        kwargs = {}
        collection = self._collection(queue_name, project)

        # NOTE(kgriffs): Claimed messages bust be queried from
        # the primary to avoid a race condition caused by the
        # multi-phased "create claim" algorithm.
        # NOTE(flaper87): In pymongo 3.0 PRIMARY is the default and
        # `read_preference` is read only. We'd need to set it when the
        # client is created.
        msgs = collection.find(query, sort=[('k', 1)], **kwargs).hint(
            CLAIMED_INDEX_FIELDS)

        if limit is not None:
            msgs = msgs.limit(limit)

        now = timeutils.utcnow_ts()

        def denormalizer(msg):
            doc = _basic_message(msg, now)
            doc['claim'] = msg['c']

            return doc

        return utils.HookedCursor(msgs, denormalizer)

    def _unclaim(self, queue_name, claim_id, project=None):
        cid = utils.to_oid(claim_id)

        # NOTE(cpp-cabrera): early abort - avoid a DB query if we're handling
        # an invalid ID
        if cid is None:
            return

        # NOTE(cpp-cabrera):  unclaim by setting the claim ID to None
        # and the claim expiration time to now
        now = timeutils.utcnow_ts()
        scope = utils.scope_queue_name(queue_name, project)
        collection = self._collection(queue_name, project)

        collection.update_many({PROJ_QUEUE: scope, 'c.id': cid},
                               {'$set': {'c': {'id': None, 'e': now}}},
                               upsert=False)

    def _inc_counter(self, queue_name, project=None, amount=1, window=None):
        """Increments the message counter and returns the new value.

        :param queue_name: Name of the queue to which the counter is scoped
        :param project: Queue's project name
        :param amount: (Default 1) Amount by which to increment the counter
        :param window: (Default None) A time window, in seconds, that
            must have elapsed since the counter was last updated, in
            order to increment the counter.

        :returns: Updated message counter value, or None if window
            was specified, and the counter has already been updated
            within the specified time period.

        :raises QueueDoesNotExist: if not found
        """

        # NOTE(flaper87): If this `if` is True, it means we're
        # using a mongodb in the control plane. To avoid breaking
        # environments doing so already, we'll keep using the counter
        # in the mongodb queue_controller rather than the one in the
        # message_controller. This should go away, eventually
        if hasattr(self._queue_ctrl, '_inc_counter'):
            return self._queue_ctrl._inc_counter(queue_name, project,
                                                 amount, window)

        now = timeutils.utcnow_ts()

        update = {'$inc': {'c.v': amount}, '$set': {'c.t': now}}
        query = _get_scoped_query(queue_name, project)
        if window is not None:
            threshold = now - window
            query['c.t'] = {'$lt': threshold}

        while True:
            try:
                collection = self._collection(queue_name, project).stats
                doc = collection.find_one_and_update(
                    query, update,
                    return_document=pymongo.ReturnDocument.AFTER,
                    projection={'c.v': 1, '_id': 0})

                break
            except pymongo.errors.AutoReconnect as ex:
                LOG.exception(ex)

        if doc is None:
            if window is None:
                # NOTE(kgriffs): Since we did not filter by a time window,
                # the queue should have been found and updated. Perhaps
                # the queue has been deleted?
                message = (u'Failed to increment the message '
                           u'counter for queue %(name)s and '
                           u'project %(project)s')
                message %= dict(name=queue_name, project=project)

                LOG.warning(message)

                raise errors.QueueDoesNotExist(queue_name, project)

            # NOTE(kgriffs): Assume the queue existed, but the counter
            # was recently updated, causing the range query on 'c.t' to
            # exclude the record.
            return None

        return doc['c']['v']

    def _get_counter(self, queue_name, project=None):
        """Retrieves the current message counter value for a given queue.

        This helper is used to generate monotonic pagination
        markers that are saved as part of the message
        document.

        Note 1: Markers are scoped per-queue and so are *not*
            globally unique or globally ordered.

        Note 2: If two or more requests to this method are made
            in parallel, this method will return the same counter
            value. This is done intentionally so that the caller
            can detect a parallel message post, allowing it to
            mitigate race conditions between producer and
            observer clients.

        :param queue_name: Name of the queue to which the counter is scoped
        :param project: Queue's project
        :returns: current message counter as an integer
        """

        # NOTE(flaper87): If this `if` is True, it means we're
        # using a mongodb in the control plane. To avoid breaking
        # environments doing so already, we'll keep using the counter
        # in the mongodb queue_controller rather than the one in the
        # message_controller. This should go away, eventually
        if hasattr(self._queue_ctrl, '_get_counter'):
            return self._queue_ctrl._get_counter(queue_name, project)

        update = {'$inc': {'c.v': 0, 'c.t': 0}}
        query = _get_scoped_query(queue_name, project)

        try:
            collection = self._collection(queue_name, project).stats
            doc = collection.find_one_and_update(
                query, update, upsert=True,
                return_document=pymongo.ReturnDocument.AFTER,
                projection={'c.v': 1, '_id': 0})

            return doc['c']['v']
        except pymongo.errors.AutoReconnect as ex:
            LOG.exception(ex)

    # ----------------------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------------------

    def list(self, queue_name, project=None, marker=None,
             limit=storage.DEFAULT_MESSAGES_PER_PAGE,
             echo=False, client_uuid=None, include_claimed=False):

        if marker is not None:
            try:
                marker = int(marker)
            except ValueError:
                yield iter([])

        messages = self._list(queue_name, project=project, marker=marker,
                              client_uuid=client_uuid, echo=echo,
                              include_claimed=include_claimed, limit=limit)

        marker_id = {}

        now = timeutils.utcnow_ts()

        # NOTE (kgriffs) @utils.raises_conn_error not needed on this
        # function, since utils.HookedCursor already has it.
        def denormalizer(msg):
            marker_id['next'] = msg['k']

            return _basic_message(msg, now)

        yield utils.HookedCursor(messages, denormalizer)
        yield str(marker_id['next'])

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def first(self, queue_name, project=None, sort=1):
        cursor = self._list(queue_name, project=project,
                            include_claimed=True, sort=sort,
                            limit=1)
        try:
            message = next(cursor)
        except StopIteration:
            raise errors.QueueIsEmpty(queue_name, project)

        now = timeutils.utcnow_ts()
        return _basic_message(message, now)

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def get(self, queue_name, message_id, project=None):
        mid = utils.to_oid(message_id)
        if mid is None:
            raise errors.MessageDoesNotExist(message_id, queue_name,
                                             project)

        now = timeutils.utcnow_ts()

        query = {
            '_id': mid,
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
        }

        collection = self._collection(queue_name, project)
        message = list(collection.find(query).limit(1).hint(ID_INDEX_FIELDS))

        if not message:
            raise errors.MessageDoesNotExist(message_id, queue_name,
                                             project)

        return _basic_message(message[0], now)

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def bulk_get(self, queue_name, message_ids, project=None):
        message_ids = [mid for mid in map(utils.to_oid, message_ids) if mid]
        if not message_ids:
            return iter([])

        now = timeutils.utcnow_ts()

        # Base query, always check expire time
        query = {
            '_id': {'$in': message_ids},
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
        }

        collection = self._collection(queue_name, project)

        # NOTE(flaper87): Should this query
        # be sorted?
        messages = collection.find(query).hint(ID_INDEX_FIELDS)

        def denormalizer(msg):
            return _basic_message(msg, now)

        return utils.HookedCursor(messages, denormalizer)

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def post(self, queue_name, messages, client_uuid, project=None):
        # NOTE(flaper87): This method should be safe to retry on
        # autoreconnect, since we've a 2-step insert for messages.
        # The worst-case scenario is that we'll increase the counter
        # several times and we'd end up with some non-active messages.

        if not self._queue_ctrl.exists(queue_name, project):
            raise errors.QueueDoesNotExist(queue_name, project)

        # NOTE(flaper87): Make sure the counter exists. This method
        # is an upsert.
        self._get_counter(queue_name, project)
        now = timeutils.utcnow_ts()
        now_dt = datetime.datetime.utcfromtimestamp(now)
        collection = self._collection(queue_name, project)

        messages = list(messages)
        msgs_n = len(messages)
        next_marker = self._inc_counter(queue_name,
                                        project,
                                        amount=msgs_n) - msgs_n

        prepared_messages = [
            {
                PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
                't': message['ttl'],
                'e': now_dt + datetime.timedelta(seconds=message['ttl']),
                'u': client_uuid,
                'c': {'id': None, 'e': now, 'c': 0},
                'b': message['body'] if 'body' in message else {},
                'k': next_marker + index,
                'tx': None,
            }

            for index, message in enumerate(messages)
        ]

        ids = collection.insert(prepared_messages, check_keys=False)

        return [str(id_) for id_ in ids]

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def delete(self, queue_name, message_id, project=None, claim=None):
        # NOTE(cpp-cabrera): return early - this is an invalid message
        # id so we won't be able to find it any way
        mid = utils.to_oid(message_id)
        if mid is None:
            return

        collection = self._collection(queue_name, project)

        query = {
            '_id': mid,
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
        }

        cid = utils.to_oid(claim)
        if cid is None:
            raise errors.ClaimDoesNotExist(claim, queue_name, project)

        now = timeutils.utcnow_ts()
        cursor = collection.find(query).hint(ID_INDEX_FIELDS)

        try:
            message = next(cursor)
        except StopIteration:
            return

        if claim is None:
            if _is_claimed(message, now):
                raise errors.MessageIsClaimed(message_id)

        else:
            if message['c']['id'] != cid:
                kwargs = {}
                # NOTE(flaper87): In pymongo 3.0 PRIMARY is the default and
                # `read_preference` is read only. We'd need to set it when the
                # client is created.
                # NOTE(kgriffs): Read from primary in case the message
                # was just barely claimed, and claim hasn't made it to
                # the secondary.
                message = collection.find_one(query, **kwargs)

                if message['c']['id'] != cid:
                    if _is_claimed(message, now):
                        raise errors.MessageNotClaimedBy(message_id, claim)

                    raise errors.MessageNotClaimed(message_id)

        collection.delete_one(query)

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def bulk_delete(self, queue_name, message_ids, project=None):
        message_ids = [mid for mid in map(utils.to_oid, message_ids) if mid]
        query = {
            '_id': {'$in': message_ids},
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
        }

        collection = self._collection(queue_name, project)
        collection.delete_many(query)

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def pop(self, queue_name, limit, project=None):
        query = {
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
        }

        # Only include messages that are not part of
        # any claim, or are part of an expired claim.
        now = timeutils.utcnow_ts()
        query['c.e'] = {'$lte': now}

        collection = self._collection(queue_name, project)
        projection = {'_id': 1, 't': 1, 'b': 1, 'c.id': 1}

        messages = (collection.find_one_and_delete(query,
                                                   projection=projection)
                    for _ in range(limit))

        final_messages = [_basic_message(message, now)
                          for message in messages
                          if message]

        return final_messages


class FIFOMessageController(MessageController):

    def _ensure_indexes(self, collection):
        """Ensures that all indexes are created."""

        collection.ensure_index(TTL_INDEX_FIELDS,
                                name='ttl',
                                expireAfterSeconds=0,
                                background=True)

        collection.ensure_index(ACTIVE_INDEX_FIELDS,
                                name='active',
                                background=True)

        collection.ensure_index(CLAIMED_INDEX_FIELDS,
                                name='claimed',
                                background=True)

        collection.ensure_index(COUNTING_INDEX_FIELDS,
                                name='counting',
                                background=True)

        # NOTE(kgriffs): This index must be unique so that
        # inserting a message with the same marker to the
        # same queue will fail; this is used to detect a
        # race condition which can cause an observer client
        # to miss a message when there is more than one
        # producer posting messages to the same queue, in
        # parallel.
        collection.ensure_index(MARKER_INDEX_FIELDS,
                                name='queue_marker',
                                unique=True,
                                background=True)

        collection.ensure_index(TRANSACTION_INDEX_FIELDS,
                                name='transaction',
                                background=True)

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def post(self, queue_name, messages, client_uuid, project=None):
        # NOTE(flaper87): This method should be safe to retry on
        # autoreconnect, since we've a 2-step insert for messages.
        # The worst-case scenario is that we'll increase the counter
        # several times and we'd end up with some non-active messages.

        if not self._queue_ctrl.exists(queue_name, project):
            raise errors.QueueDoesNotExist(queue_name, project)

        # NOTE(flaper87): Make sure the counter exists. This method
        # is an upsert.
        self._get_counter(queue_name, project)
        now = timeutils.utcnow_ts()
        now_dt = datetime.datetime.utcfromtimestamp(now)
        collection = self._collection(queue_name, project)

        # Set the next basis marker for the first attempt.
        #
        # Note that we don't increment the counter right away because
        # if 2 concurrent posts happen and the one with the higher counter
        # ends before the one with the lower counter, there's a window
        # where a client paging through the queue may get the messages
        # with the higher counter and skip the previous ones. This would
        # make our FIFO guarantee unsound.
        next_marker = self._get_counter(queue_name, project)

        # Unique transaction ID to facilitate atomic batch inserts
        transaction = objectid.ObjectId()

        prepared_messages = [
            {
                PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
                't': message['ttl'],
                'e': now_dt + datetime.timedelta(seconds=message['ttl']),
                'u': client_uuid,
                'c': {'id': None, 'e': now, 'c': 0},
                'b': message['body'] if 'body' in message else {},
                'k': next_marker + index,
                'tx': transaction,
            }

            for index, message in enumerate(messages)
        ]

        # NOTE(kgriffs): Don't take the time to do a 2-phase insert
        # if there is no way for it to partially succeed.
        if len(prepared_messages) == 1:
            transaction = None
            prepared_messages[0]['tx'] = None

        # Use a retry range for sanity, although we expect
        # to rarely, if ever, reach the maximum number of
        # retries.
        #
        # NOTE(kgriffs): With the default configuration (100 ms
        # max sleep, 1000 max attempts), the max stall time
        # before the operation is abandoned is 49.95 seconds.
        for attempt in self._retry_range:
            try:
                ids = collection.insert(prepared_messages, check_keys=False)

                # Log a message if we retried, for debugging perf issues
                if attempt != 0:
                    msgtmpl = _(u'%(attempts)d attempt(s) required to post '
                                u'%(num_messages)d messages to queue '
                                u'"%(queue)s" under project %(project)s')

                    LOG.debug(msgtmpl,
                              dict(queue=queue_name,
                                   attempts=attempt + 1,
                                   num_messages=len(ids),
                                   project=project))

                # Update the counter in preparation for the next batch
                #
                # NOTE(kgriffs): Due to the unique index on the messages
                # collection, competing inserts will fail as a whole,
                # and keep retrying until the counter is incremented
                # such that the competing marker's will start at a
                # unique number, 1 past the max of the messages just
                # inserted above.
                self._inc_counter(queue_name, project, amount=len(ids))

                # NOTE(kgriffs): Finalize the insert once we can say that
                # all the messages made it. This makes bulk inserts
                # atomic, assuming queries filter out any non-finalized
                # messages.
                if transaction is not None:
                    collection.update_many({'tx': transaction},
                                           {'$set': {'tx': None}},
                                           upsert=False)

                return [str(id_) for id_ in ids]

            except pymongo.errors.DuplicateKeyError as ex:
                # TODO(kgriffs): Record stats of how often retries happen,
                # and how many attempts, on average, are required to insert
                # messages.

                # NOTE(kgriffs): This can be used in conjunction with the
                # log line, above, that is emitted after all messages have
                # been posted, to gauge how long it is taking for messages
                # to be posted to a given queue, or overall.
                #
                # TODO(kgriffs): Add transaction ID to help match up loglines
                if attempt == 0:
                    msgtmpl = _(u'First attempt failed while '
                                u'adding messages to queue '
                                u'"%(queue)s" under project %(project)s')

                    LOG.debug(msgtmpl, dict(queue=queue_name, project=project))

                # NOTE(kgriffs): Never retry past the point that competing
                # messages expire and are GC'd, since once they are gone,
                # the unique index no longer protects us from getting out
                # of order, which could cause an observer to miss this
                # message. The code below provides a sanity-check to ensure
                # this situation can not happen.
                elapsed = timeutils.utcnow_ts() - now
                if elapsed > MAX_RETRY_POST_DURATION:
                    msgtmpl = (u'Exceeded maximum retry duration for queue '
                               u'"%(queue)s" under project %(project)s')

                    LOG.warning(msgtmpl,
                                dict(queue=queue_name, project=project))
                    break

                # Chill out for a moment to mitigate thrashing/thundering
                self._backoff_sleep(attempt)

                # NOTE(kgriffs): Perhaps we failed because a worker crashed
                # after inserting messages, but before incrementing the
                # counter; that would cause all future requests to stall,
                # since they would keep getting the same base marker that is
                # conflicting with existing messages, until the messages that
                # "won" expire, at which time we would end up reusing markers,
                # and that could make some messages invisible to an observer
                # that is querying with a marker that is large than the ones
                # being reused.
                #
                # To mitigate this, we apply a heuristic to determine whether
                # a counter has stalled. We attempt to increment the counter,
                # but only if it hasn't been updated for a few seconds, which
                # should mean that nobody is left to update it!
                #
                # Note that we increment one at a time until the logjam is
                # broken, since we don't know how many messages were posted
                # by the worker before it crashed.
                next_marker = self._inc_counter(
                    queue_name, project, window=COUNTER_STALL_WINDOW)

                # Retry the entire batch with a new sequence of markers.
                #
                # NOTE(kgriffs): Due to the unique index, and how
                # MongoDB works with batch requests, we will never
                # end up with a partially-successful update. The first
                # document in the batch will fail to insert, and the
                # remainder of the documents will not be attempted.
                if next_marker is None:
                    # NOTE(kgriffs): Usually we will end up here, since
                    # it should be rare that a counter becomes stalled.
                    next_marker = self._get_counter(
                        queue_name, project)
                else:
                    msgtmpl = (u'Detected a stalled message counter '
                               u'for queue "%(queue)s" under '
                               u'project %(project)s.'
                               u'The counter was incremented to %(value)d.')

                    LOG.warning(msgtmpl,
                                dict(queue=queue_name,
                                     project=project,
                                     value=next_marker))

                for index, message in enumerate(prepared_messages):
                    message['k'] = next_marker + index

            except Exception as ex:
                LOG.exception(ex)
                raise

        msgtmpl = (u'Hit maximum number of attempts (%(max)s) for queue '
                   u'"%(queue)s" under project %(project)s')

        LOG.warning(msgtmpl,
                    dict(max=self.driver.mongodb_conf.max_attempts,
                         queue=queue_name,
                         project=project))

        raise errors.MessageConflict(queue_name, project)


def _is_claimed(msg, now):
    return (msg['c']['id'] is not None and
            msg['c']['e'] > now)


def _basic_message(msg, now):
    oid = msg['_id']
    age = now - utils.oid_ts(oid)

    return {
        'id': str(oid),
        'age': int(age),
        'ttl': msg['t'],
        'body': msg['b'],
        'claim_id': str(msg['c']['id']) if msg['c']['id'] else None
    }


class MessageQueueHandler(object):

    def __init__(self, driver, control_driver):
        self.driver = driver
        self._cache = self.driver.cache
        self.queue_controller = self.driver.queue_controller
        self.message_controller = self.driver.message_controller

    def delete(self, queue_name, project=None):
        self.message_controller._purge_queue(queue_name, project)

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def stats(self, name, project=None):
        if not self.queue_controller.exists(name, project=project):
            raise errors.QueueDoesNotExist(name, project)

        controller = self.message_controller

        active = controller._count(name, project=project,
                                   include_claimed=False)

        total = controller._count(name, project=project,
                                  include_claimed=True)

        message_stats = {
            'claimed': total - active,
            'free': active,
            'total': total,
        }

        try:
            oldest = controller.first(name, project=project, sort=1)
            newest = controller.first(name, project=project, sort=-1)
        except errors.QueueIsEmpty:
            pass
        else:
            now = timeutils.utcnow_ts()
            message_stats['oldest'] = utils.stat_message(oldest, now)
            message_stats['newest'] = utils.stat_message(newest, now)

        return {'messages': message_stats}


def _get_scoped_query(name, project):
    return {'p_q': utils.scope_queue_name(name, project)}

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

import pymongo.errors
import pymongo.read_preferences

import marconi.openstack.common.log as logging
from marconi.openstack.common import timeutils
from marconi.queues import storage
from marconi.queues.storage import errors
from marconi.queues.storage.mongodb import utils


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

# Index used to ensure uniqueness.
MARKER_INDEX_FIELDS = [
    (PROJ_QUEUE, 1),
    ('k', 1),
]


class MessageController(storage.MessageBase):
    """Implements message resource operations using MongoDB.

    Messages are scoped by project + queue.

    Messages:
        Name        Field
        -----------------
        scope    ->   p_q
        expires  ->     e
        ttl      ->     t
        uuid     ->     u
        claim    ->     c
        marker   ->     k
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
        # would provide access to marconi_p2.messages (partition numbers are
        # zero-based).
        self._collections = [db.messages
                             for db in self.driver.message_databases]

        # Ensure indexes are initialized before any queries are performed
        for collection in self._collections:
            self._ensure_indexes(collection)

    #-----------------------------------------------------------------------
    # Helpers
    #-----------------------------------------------------------------------

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
        collection.remove({PROJ_QUEUE: scope}, w=0)

    def _list(self, queue_name, project=None, marker=None,
              echo=False, client_uuid=None, fields=None,
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
        :param fields: (Default None) Fields to include in emmitted
            documents
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
            # Messages must belong to this
            # queue and project
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
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
        cursor = collection.find(query, fields=fields,
                                 sort=[('k', sort)], limit=limit)

        # NOTE(flaper87): Suggest the index to use for this query to
        # ensure the most performant one is chosen.
        return cursor.hint(ACTIVE_INDEX_FIELDS)

    #-----------------------------------------------------------------------
    # "Friends" interface
    #-----------------------------------------------------------------------

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
            # Messages must belong to this queue
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
        }

        if not include_claimed:
            # Exclude messages that are claimed
            query['c.e'] = {'$lte': timeutils.utcnow_ts()}

        collection = self._collection(queue_name, project)
        return collection.find(query).hint(COUNTING_INDEX_FIELDS).count()

    def _active(self, queue_name, marker=None, echo=False,
                client_uuid=None, fields=None, project=None,
                limit=None):

        return self._list(queue_name, project=project, marker=marker,
                          echo=echo, client_uuid=client_uuid,
                          fields=fields, include_claimed=False,
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

        # NOTE(kgriffs): Claimed messages bust be queried from
        # the primary to avoid a race condition caused by the
        # multi-phased "create claim" algorithm.
        preference = pymongo.read_preferences.ReadPreference.PRIMARY
        collection = self._collection(queue_name, project)
        msgs = collection.find(query, sort=[('k', 1)],
                               read_preference=preference).hint(
                                   CLAIMED_INDEX_FIELDS
                               )

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

        collection.update({PROJ_QUEUE: scope, 'c.id': cid},
                          {'$set': {'c': {'id': None, 'e': now}}},
                          upsert=False, multi=True)

    #-----------------------------------------------------------------------
    # Public interface
    #-----------------------------------------------------------------------

    def list(self, queue_name, project=None, marker=None, limit=None,
             echo=False, client_uuid=None, include_claimed=False):

        if limit is None:
            limit = self.driver.limits_conf.default_message_paging

        if marker is not None:
            try:
                marker = int(marker)
            except ValueError:
                yield iter([])

        messages = self._list(queue_name, project=project, marker=marker,
                              client_uuid=client_uuid,  echo=echo,
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
    def first(self, queue_name, project=None, sort=1):
        cursor = self._list(queue_name, project=project,
                            include_claimed=True, sort=sort,
                            limit=1)
        try:
            message = next(cursor)
        except StopIteration:
            raise errors.QueueIsEmpty(queue_name, project)

        return message

    @utils.raises_conn_error
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
    def post(self, queue_name, messages, client_uuid, project=None):
        if not self._queue_ctrl.exists(queue_name, project):
            raise errors.QueueDoesNotExist(queue_name, project)

        now = timeutils.utcnow_ts()
        now_dt = datetime.datetime.utcfromtimestamp(now)
        collection = self._collection(queue_name, project)

        # Set the next basis marker for the first attempt.
        next_marker = self._queue_ctrl._get_counter(queue_name, project)

        prepared_messages = [
            {
                't': message['ttl'],
                PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
                'e': now_dt + datetime.timedelta(seconds=message['ttl']),
                'u': client_uuid,
                'c': {'id': None, 'e': now},
                'b': message['body'] if 'body' in message else {},
                'k': next_marker + index,
            }

            for index, message in enumerate(messages)
        ]

        # Use a retry range for sanity, although we expect
        # to rarely, if ever, reach the maximum number of
        # retries.
        #
        # NOTE(kgriffs): With the default configuration (100 ms
        # max sleep, 1000 max attempts), the max stall time
        # before the operation is abandoned is 49.95 seconds.
        for attempt in self._retry_range:
            try:
                ids = collection.insert(prepared_messages)

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
                self._queue_ctrl._inc_counter(queue_name, project,
                                              amount=len(ids))

                return map(str, ids)

            except pymongo.errors.DuplicateKeyError as ex:
                # Try again with the remaining messages

                # TODO(kgriffs): Record stats of how often retries happen,
                # and how many attempts, on average, are required to insert
                # messages.

                # NOTE(kgriffs): This can be used in conjunction with the
                # log line, above, that is emitted after all messages have
                # been posted, to guage how long it is taking for messages
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
                    msgtmpl = _(u'Exceeded maximum retry duration for queue '
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
                next_marker = self._queue_ctrl._inc_counter(
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
                    next_marker = self._queue_ctrl._get_counter(
                        queue_name, project)
                else:
                    msgtmpl = (u'Detected a stalled message counter for '
                               u'queue "%(queue)s" under project %(project)s. '
                               u'The counter was incremented to %(value)d.')

                    LOG.warning(msgtmpl,
                                dict(queue=queue_name,
                                     project=project,
                                     value=next_marker))

                for index, message in enumerate(prepared_messages):
                    message['k'] = next_marker + index

            except Exception as ex:
                # TODO(kgriffs): Query the DB to get the last marker that
                # made it, and extrapolate from there to figure out what
                # needs to be retried.

                LOG.exception(ex)
                raise

        msgtmpl = _(u'Hit maximum number of attempts (%(max)s) for queue '
                    u'"%(queue)s" under project %(project)s')

        LOG.warning(msgtmpl,
                    dict(max=self.driver.mongodb_conf.max_attempts,
                         queue=queue_name,
                         project=project))

        succeeded_ids = []
        raise errors.MessageConflict(queue_name, project,
                                     succeeded_ids)

    @utils.raises_conn_error
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

        # NOTE(cpp-cabrera): return early - the user gaves us an
        # invalid claim id and that renders the rest of this
        # request moot
        cid = utils.to_oid(claim)
        if cid is None:
            return

        now = timeutils.utcnow_ts()
        cursor = collection.find(query).hint(ID_INDEX_FIELDS)

        try:
            message = next(cursor)
        except StopIteration:
            return

        is_claimed = (message['c']['id'] is not None and
                      message['c']['e'] > now)

        if claim is None:
            if is_claimed:
                raise errors.MessageIsClaimed(message_id)

        else:
            if message['c']['id'] != cid:
                # NOTE(kgriffs): Read from primary in case the message
                # was just barely claimed, and claim hasn't made it to
                # the secondary.
                pref = pymongo.read_preferences.ReadPreference.PRIMARY
                message = collection.find_one(query, read_preference=pref)

                if message['c']['id'] != cid:
                    raise errors.MessageIsClaimedBy(message_id, claim)

        collection.remove(query['_id'], w=0)

    @utils.raises_conn_error
    def bulk_delete(self, queue_name, message_ids, project=None):
        message_ids = [mid for mid in map(utils.to_oid, message_ids) if mid]
        query = {
            '_id': {'$in': message_ids},
            PROJ_QUEUE: utils.scope_queue_name(queue_name, project),
        }

        collection = self._collection(queue_name, project)
        collection.remove(query, w=0)


def _basic_message(msg, now):
    oid = msg['_id']
    age = now - utils.oid_ts(oid)

    return {
        'id': str(oid),
        'age': int(age),
        'ttl': msg['t'],
        'body': msg['b'],
    }

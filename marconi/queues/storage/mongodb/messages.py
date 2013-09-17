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

import time

import pymongo.errors
import pymongo.read_preferences

from marconi.common import config
import marconi.openstack.common.log as logging
from marconi.openstack.common import timeutils
from marconi.queues import storage
from marconi.queues.storage import exceptions
from marconi.queues.storage.mongodb import options
from marconi.queues.storage.mongodb import utils

LOG = logging.getLogger(__name__)
CFG = config.namespace('limits:storage').from_options(
    default_message_paging=10,
)

# For hinting
ID_INDEX_FIELDS = [('_id', 1)]

# NOTE(kgriffs): This index is for listing messages, usually
# filtering out claimed ones.
ACTIVE_INDEX_FIELDS = [
    ('p', 1),  # Project will to be unique, so put first
    ('q', 1),  # May not be unique, since user names it
    ('k', 1),  # Used for sorting and paging, must come before range queries
    ('c.e', 1),  # Used for filtering out claimed messages
]

# For counting
COUNTING_INDEX_FIELDS = [
    ('p', 1),  # Project will to be unique, so put first
    ('q', 1),  # May not be unique, since user names it
    ('c.e', 1),  # Used for filtering out claimed messages
]

# Index used for claims
CLAIMED_INDEX_FIELDS = [
    ('p', 1),
    ('q', 1),
    ('c.id', 1),
    ('k', 1),
    ('c.e', 1),
]

# Index used for _next_marker() and also to ensure uniqueness.
MARKER_INDEX_FIELDS = [
    ('p', 1),
    ('q', 1),
    ('k', -1)
]


class MessageController(storage.MessageBase):
    """Implements message resource operations using MongoDB.

    Messages:
        Name        Field
        -----------------
        queue_name ->   q
        expires    ->   e
        ttl        ->   t
        uuid       ->   u
        claim      ->   c
        marker     ->   k
    """

    def __init__(self, *args, **kwargs):
        super(MessageController, self).__init__(*args, **kwargs)

        # Cache for convenience and performance (avoids extra lookups and
        # recreating the range for every request.)
        self._queue_controller = self.driver.queue_controller
        self._db = self.driver.db
        self._retry_range = range(options.CFG.max_attempts)

        # Make sure indexes exist before,
        # doing anything.
        self._col = self._db['messages']

        self._ensure_indexes()

    #-----------------------------------------------------------------------
    # Helpers
    #-----------------------------------------------------------------------

    def _ensure_indexes(self):
        """Ensures that all indexes are created."""

        self._col.ensure_index(ACTIVE_INDEX_FIELDS,
                               name='active',
                               background=True)

        self._col.ensure_index(CLAIMED_INDEX_FIELDS,
                               name='claimed',
                               background=True)

        self._col.ensure_index(COUNTING_INDEX_FIELDS,
                               name='counting',
                               background=True)

        # NOTE(kgriffs): This index must be unique so that
        # inserting a message with the same marker to the
        # same queue will fail; this is used to detect a
        # race condition which can cause an observer client
        # to miss a message when there is more than one
        # producer posting messages to the same queue, in
        # parallel.
        self._col.ensure_index(MARKER_INDEX_FIELDS,
                               name='queue_marker',
                               unique=True,
                               background=True)

    def _next_marker(self, queue_name, project=None):
        """Retrieves the next message marker for a given queue.

        This helper is used to generate monotonic pagination
        markers that are saved as part of the message
        document. Simply taking the max of the current message
        markers works, since Marconi always leaves the most recent
        message in the queue (new queues always return 1).

        Note 1: Markers are scoped per-queue and so are *not*
            globally unique or globally ordered.

        Note 2: If two or more requests to this method are made
            in parallel, this method will return the same
            marker. This is done intentionally so that the caller
            can detect a parallel message post, allowing it to
            mitigate race conditions between producer and
            observer clients.

        :param queue_name: Determines the scope for the marker
        :param project: Queue's project
        :returns: next message marker as an integer
        """

        document = self._col.find_one({'p': project, 'q': queue_name},
                                      sort=[('k', -1)],
                                      fields={'k': 1, '_id': 0})

        return 1 if document is None else (document['k'] + 1)

    def _backoff_sleep(self, attempt):
        """Sleep between retries using a jitter algorithm.

        Mitigates thrashing between multiple parallel requests, and
        creates backpressure on clients to slow down the rate
        at which they submit requests.

        :param attempt: current attempt number, zero-based
        """
        seconds = utils.calculate_backoff(attempt, options.CFG.max_attempts,
                                          options.CFG.max_retry_sleep,
                                          options.CFG.max_retry_jitter)

        time.sleep(seconds)

    def _remove_expired(self, queue_name, project):
        """Removes all expired messages except for the most recent
        in each queue.

        This method is used in lieu of mongo's TTL index since we
        must always leave at least one message in the queue for
        calculating the next marker.

        :param queue_name: name for the queue from which to remove
            expired messages
        :param project: Project queue_name belong's too
        """

        # Get the message with the highest marker, and leave
        # it in the queue
        head = self._col.find_one({'p': project, 'q': queue_name},
                                  sort=[('k', -1)], fields={'k': 1})

        if head is None:
            # Assume queue was just deleted via a parallel request
            LOG.debug(_(u'Queue %s is empty or missing.') % queue_name)
            return

        query = {
            'p': project,
            'q': queue_name,
            'k': {'$ne': head['k']},
            'e': {'$lte': timeutils.utcnow_ts()},
        }

        self._col.remove(query, w=0)

    def _purge_queue(self, queue_name, project=None):
        """Removes all messages from the queue.

        Warning: Only use this when deleting the queue; otherwise
        you can cause a side-effect of reseting the marker counter
        which can cause clients to miss tons of messages.

        If the queue does not exist, this method fails silently.

        :param queue_name: name of the queue to purge
        :param project: ID of the project to which the queue belongs
        """
        self._col.remove({'p': project, 'q': queue_name}, w=0)

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
            'p': project,
            'q': queue_name,

            # The messages cannot be expired
            'e': {'$gt': now},
        }

        if not echo:
            query['u'] = {'$ne': client_uuid}

        if marker is not None:
            query['k'] = {'$gt': marker}

        if not include_claimed:
            # Only include messages that are not part of
            # any claim, or are part of an expired claim.
            query['c.e'] = {'$lte': now}

        # Construct the request
        cursor = self._col.find(query, fields=fields,
                                sort=[('k', sort)], limit=limit)

        # NOTE(flaper87): Suggest the index to use for this query
        return cursor.hint(ACTIVE_INDEX_FIELDS)

    #-----------------------------------------------------------------------
    # Interface
    #-----------------------------------------------------------------------

    def count(self, queue_name, project=None, include_claimed=False):
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
            'p': project,
            'q': queue_name,

            # The messages can not be expired
            'e': {'$gt': timeutils.utcnow_ts()},
        }

        if not include_claimed:
            # Exclude messages that are claimed
            query['c.e'] = {'$lte': timeutils.utcnow_ts()}

        return self._col.find(query).hint(COUNTING_INDEX_FIELDS).count()

    def first(self, queue_name, project=None, sort=1):
        """Get first message in the queue (including claimed).

        :param queue_name: Name of the queue to list
        :param sort: (Default 1) Sort order for the listing. Pass 1 for
            ascending (oldest message first), or -1 for descending (newest
            message first).

        :returns: First message in the queue, or None if the queue is
            empty

        """
        cursor = self._list(queue_name, project=project,
                            include_claimed=True, sort=sort,
                            limit=1)
        try:
            message = next(cursor)
        except StopIteration:
            raise exceptions.QueueIsEmpty(queue_name, project)

        return message

    def active(self, queue_name, marker=None, echo=False,
               client_uuid=None, fields=None, project=None,
               limit=None):

        return self._list(queue_name, project=project, marker=marker,
                          echo=echo, client_uuid=client_uuid,
                          fields=fields, include_claimed=False,
                          limit=limit)

    def claimed(self, queue_name, claim_id,
                expires=None, limit=None, project=None):

        if claim_id is None:
            claim_id = {'$ne': None}

        query = {
            'p': project,
            'q': queue_name,
            'c.id': claim_id,
            'c.e': {'$gt': expires or timeutils.utcnow_ts()},
        }

        # NOTE(kgriffs): Claimed messages bust be queried from
        # the primary to avoid a race condition caused by the
        # multi-phased "create claim" algorithm.
        preference = pymongo.read_preferences.ReadPreference.PRIMARY
        msgs = self._col.find(query, sort=[('k', 1)],
                              read_preference=preference)

        if limit is not None:
            msgs = msgs.limit(limit)

        now = timeutils.utcnow_ts()

        def denormalizer(msg):
            doc = _basic_message(msg, now)
            doc['claim'] = msg['c']

            return doc

        return utils.HookedCursor(msgs, denormalizer)

    def unclaim(self, queue_name, claim_id, project=None):
        cid = utils.to_oid(claim_id)

        # NOTE(cpp-cabrera): early abort - avoid a DB query if we're handling
        # an invalid ID
        if cid is None:
            return

        # NOTE(cpp-cabrera):  unclaim by setting the claim ID to None
        # and the claim expiration time to now
        now = timeutils.utcnow_ts()
        self._col.update({'p': project, 'q': queue_name, 'c.id': cid},
                         {'$set': {'c': {'id': None, 'e': now}}},
                         upsert=False, multi=True)

    def remove_expired(self):
        """Removes all expired messages except for the most recent
        in each queue.

        This method is used in lieu of mongo's TTL index since we
        must always leave at least one message in the queue for
        calculating the next marker.

        Warning: This method is expensive, since it must perform
        separate queries for each queue, due to the requirement that
        it must leave at least one message in each queue, and it
        is impractical to send a huge list of _id's to filter out
        in a single call. That being said, this is somewhat mitigated
        by the fact that remove() is run on each queue seperately,
        thereby reducing the duration that any given lock is held.
        """

        # TODO(kgriffs): Optimize first by batching the .removes, second
        # by setting a 'last inserted ID' in the queue collection for
        # each message inserted (TBD, may cause problematic side-effect),
        # and third, by changing the marker algorithm such that it no
        # longer depends on retaining the last message in the queue!
        for name, project in self._queue_controller._get_np():
            self._remove_expired(name, project)

    def list(self, queue_name, project=None, marker=None, limit=None,
             echo=False, client_uuid=None, include_claimed=False):

        if limit is None:
            limit = CFG.default_message_paging

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

        def denormalizer(msg):
            marker_id['next'] = msg['k']

            return _basic_message(msg, now)

        yield utils.HookedCursor(messages, denormalizer)
        yield str(marker_id['next'])

    @utils.raises_conn_error
    def get(self, queue_name, message_id, project=None):
        """Gets a single message by ID.

        :raises: exceptions.MessageDoesNotExist
        """
        mid = utils.to_oid(message_id)
        if mid is None:
            raise exceptions.MessageDoesNotExist(message_id, queue_name,
                                                 project)

        now = timeutils.utcnow_ts()

        query = {
            '_id': mid,
            'p': project,
            'q': queue_name,
            'e': {'$gt': now}
        }

        message = list(self._col.find(query).limit(1).hint(ID_INDEX_FIELDS))

        if not message:
            raise exceptions.MessageDoesNotExist(message_id, queue_name,
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
            'p': project,
            'q': queue_name,
            'e': {'$gt': now},
        }

        # NOTE(flaper87): Should this query
        # be sorted?
        messages = self._col.find(query).hint(ID_INDEX_FIELDS)

        def denormalizer(msg):
            return _basic_message(msg, now)

        return utils.HookedCursor(messages, denormalizer)

    @utils.raises_conn_error
    def post(self, queue_name, messages, client_uuid, project=None):
        now = timeutils.utcnow_ts()

        if not self._queue_controller.exists(queue_name, project):
            raise exceptions.QueueDoesNotExist(queue_name, project)

        # Set the next basis marker for the first attempt.
        next_marker = self._next_marker(queue_name, project)

        prepared_messages = [
            {
                't': message['ttl'],
                'q': queue_name,
                'p': project,
                'e': now + message['ttl'],
                'u': client_uuid,
                'c': {'id': None, 'e': now},
                'b': message['body'] if 'body' in message else {},
                'k': next_marker + index,
            }

            for index, message in enumerate(messages)
        ]

        # Results are aggregated across all attempts
        # NOTE(kgriffs): Using lazy instantiation...
        aggregated_results = None

        # Use a retry range for sanity, although we expect
        # to rarely, if ever, reach the maximum number of
        # retries.
        for attempt in self._retry_range:
            try:
                ids = self._col.insert(prepared_messages)

                # NOTE(kgriffs): Only use aggregated results if we must,
                # which saves some cycles on the happy path.
                if aggregated_results:
                    aggregated_results.extend(ids)
                    ids = aggregated_results

                # Log a message if we retried, for debugging perf issues
                if attempt != 0:
                    message = _(u'%(attempts)d attempt(s) required to post '
                                u'%(num_messages)d messages to queue '
                                u'%(queue_name)s and project %(project)s')
                    message %= dict(queue_name=queue_name, attempts=attempt+1,
                                    num_messages=len(ids), project=project)

                    LOG.debug(message)

                return map(str, ids)

            except pymongo.errors.DuplicateKeyError as ex:
                # Try again with the remaining messages

                # NOTE(kgriffs): This can be used in conjunction with the
                # log line, above, that is emitted after all messages have
                # been posted, to guage how long it is taking for messages
                # to be posted to a given queue, or overall.
                #
                # TODO(kgriffs): Add transaction ID to help match up loglines
                if attempt == 0:
                    message = _(u'First attempt failed while '
                                u'adding messages to queue %s '
                                u'for current request') % queue_name

                    LOG.debug(message)

                # TODO(kgriffs): Record stats of how often retries happen,
                # and how many attempts, on average, are required to insert
                # messages.

                # NOTE(kgriffs): Slice prepared_messages. We have to interpret
                # the error message to get the duplicate key, which gives
                # us the marker that had a dupe, allowing us to extrapolate
                # how many messages were consumed, since markers are monotonic
                # counters.
                duplicate_marker = utils.dup_marker_from_error(str(ex))
                failed_index = duplicate_marker - next_marker

                # Put the successful one's IDs into aggregated_results.
                succeeded_messages = prepared_messages[:failed_index]
                succeeded_ids = [msg['_id'] for msg in succeeded_messages]

                # Results are aggregated across all attempts
                if aggregated_results is None:
                    aggregated_results = succeeded_ids
                else:
                    aggregated_results.extend(succeeded_ids)

                # Retry the remaining messages with a new sequence
                # of markers.
                prepared_messages = prepared_messages[failed_index:]
                next_marker = self._next_marker(queue_name, project)
                for index, message in enumerate(prepared_messages):
                    message['k'] = next_marker + index

                # Chill out for a moment to mitigate thrashing/thundering
                self._backoff_sleep(attempt)

            except Exception as ex:
                # TODO(kgriffs): Query the DB to get the last marker that
                # made it, and extrapolate from there to figure out what
                # needs to be retried.

                LOG.exception(ex)
                raise

        message = _(u'Hit maximum number of attempts (%(max)s) for queue '
                    u'%(id)s in project %(project)s')
        message %= dict(max=options.CFG.max_attempts, id=queue_name,
                        project=project)

        LOG.warning(message)

        succeeded_ids = map(str, aggregated_results)
        raise exceptions.MessageConflict(queue_name, project, succeeded_ids)

    @utils.raises_conn_error
    def delete(self, queue_name, message_id, project=None, claim=None):
        # NOTE(cpp-cabrera): return early - this is an invalid message
        # id so we won't be able to find it any way
        mid = utils.to_oid(message_id)
        if mid is None:
            return

        query = {
            '_id': mid,
            'p': project,
            'q': queue_name,
        }

        # NOTE(cpp-cabrera): return early - the user gaves us an
        # invalid claim id and that renders the rest of this
        # request moot
        cid = utils.to_oid(claim)
        if cid is None:
            return

        now = timeutils.utcnow_ts()
        query['e'] = {'$gt': now}
        message = self._col.find_one(query)

        if message is None:
            return

        is_claimed = (message['c']['id'] is not None and
                      message['c']['e'] > now)

        if claim is None:
            if is_claimed:
                raise exceptions.MessageIsClaimed(message_id)

        else:
            if message['c']['id'] != cid:
                raise exceptions.MessageIsClaimedBy(message_id, claim)

        self._col.remove(query['_id'], w=0)

    @utils.raises_conn_error
    def bulk_delete(self, queue_name, message_ids, project=None):
        message_ids = [mid for mid in map(utils.to_oid, message_ids) if mid]
        query = {
            '_id': {'$in': message_ids},
            'p': project,
            'q': queue_name,
        }

        self._col.remove(query, w=0)


def _basic_message(msg, now):
    oid = msg['_id']
    age = utils.oid_ts(oid) - now

    return {
        'id': str(oid),
        'age': int(age),
        'ttl': msg['t'],
        'body': msg['b'],
    }

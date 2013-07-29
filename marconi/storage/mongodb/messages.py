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

import collections
import datetime
import time

from bson import objectid
import pymongo.errors
import six

import marconi.openstack.common.log as logging
from marconi.openstack.common import timeutils
from marconi import storage
from marconi.storage import exceptions
from marconi.storage.mongodb import options
from marconi.storage.mongodb import utils

LOG = logging.getLogger(__name__)


class MessageController(storage.MessageBase):
    """Implements message resource operations using MongoDB.

    Messages:
        Name        Field
        -----------------
        queue_id   ->   q
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

        # NOTE(flaper87): This index is used mostly in the
        # active method but some parts of it are used in
        # other places.
        #   * q: Mostly everywhere. It must stay at the
        #       beginning of the index.
        #   * e: Together with q is used for getting a
        #       specific message. (see `get`)
        active_fields = [
            ('q', 1),
            ('e', 1),
            ('c.e', 1),
            ('k', 1),
            ('_id', -1),
        ]

        self._col.ensure_index(active_fields,
                               name='active',
                               background=True)

        # Index used for claims
        claimed_fields = [
            ('q', 1),
            ('c.id', 1),
            ('c.e', 1),
            ('_id', -1),
        ]

        self._col.ensure_index(claimed_fields,
                               name='claimed',
                               background=True)

        # Index used for _next_marker() and also to ensure
        # uniqueness.
        #
        # NOTE(kgriffs): This index must be unique so that
        # inserting a message with the same marker to the
        # same queue will fail; this is used to detect a
        # race condition which can cause an observer client
        # to miss a message when there is more than one
        # producer posting messages to the same queue, in
        # parallel.
        self._col.ensure_index([('q', 1), ('k', -1)],
                               name='queue_marker',
                               unique=True,
                               background=True)

    #-----------------------------------------------------------------------
    # Helpers
    #-----------------------------------------------------------------------

    def _get_queue_id(self, queue, project=None):
        return self._queue_controller._get_id(queue, project)

    def _get_queue_ids(self):
        return self._queue_controller._get_ids()

    def _next_marker(self, queue_id):
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

        :param queue_id: queue ID
        :returns: next message marker as an integer
        """

        document = self._col.find_one({'q': queue_id},
                                      sort=[('k', -1)],
                                      fields={'k': 1, '_id': 0})

        # NOTE(kgriffs): this approach is faster than using 'or'
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

    def _count_expired(self, queue_id):
        """Counts the number of expired messages in a queue.

        :param queue_id: id for the queue to stat
        """

        query = {
            'q': queue_id,
            'e': {'$lte': timeutils.utcnow()},
        }

        return self._col.find(query).count()

    def _remove_expired(self, queue_id):
        """Removes all expired messages except for the most recent
        in each queue.

        This method is used in lieu of mongo's TTL index since we
        must always leave at least one message in the queue for
        calculating the next marker.

        Note that expired messages are only removed if their count
        exceeds options.CFG.gc_threshold.

        :param queue_id: id for the queue from which to remove
            expired messages
        """

        if options.CFG.gc_threshold <= self._count_expired(queue_id):
            # Get the message with the highest marker, and leave
            # it in the queue
            head = self._col.find_one({'q': queue_id},
                                      sort=[('k', -1)],
                                      fields={'_id': 1})

            if head is None:
                # Assume queue was just deleted via a parallel request
                LOG.warning(_('Queue %s is empty or missing.') % queue_id)
                return

            query = {
                'q': queue_id,
                'e': {'$lte': timeutils.utcnow()},
                '_id': {'$ne': head['_id']}
            }

            self._col.remove(query)

    def _purge_queue(self, queue, project=None):
        """Removes all messages from the queue.

        Warning: Only use this when deleting the queue; otherwise
        you can cause a side-effect of reseting the marker counter
        which can cause clients to miss tons of messages.

        If the queue does not exist, this method fails silently.

        :param queue: name of the queue to purge
        :param project: name of the project to which the queue belongs
        """
        try:
            qid = self._get_queue_id(queue, project)
            self._col.remove({'q': qid}, w=0)
        except exceptions.QueueDoesNotExist:
            pass

    def _list(self, queue_id, marker=None, echo=False,
              client_uuid=None, fields=None, include_claimed=False):
        """Message document listing helper.

        :param queue_id: ObjectID of the queue to list
        :param marker: Message marker from which to start iterating
        :param echo: Whether to return messages that match client_uuid
        :param client_uuid: UUID for the client that originated this request
        :param fields: fields to include in emmitted documents
        :param include_claimed: Whether to include claimed messages,
            not just active ones

        :returns: MongoDB "find" generator
        """

        now = timeutils.utcnow()

        query = {
            # Messages must belong to this queue
            'q': queue_id,
            # The messages can not be expired
            'e': {'$gt': now},
        }

        if fields and not isinstance(fields, (dict, list)):
            raise TypeError('Fields must be an instance of list / dict')

        if not echo and client_uuid:
            query['u'] = {'$ne': client_uuid}

        if marker:
            query['k'] = {'$gt': marker}

        if not include_claimed:
            # Only include messages that are not part of
            # any claim, or are part of an expired claim.
            query['c.e'] = {'$lte': now}

        return self._col.find(query, fields=fields)

    #-----------------------------------------------------------------------
    # Interface
    #-----------------------------------------------------------------------

    def active(self, queue_id, marker=None, echo=False,
               client_uuid=None, fields=None):

        # NOTE(kgriffs): Since this is a public method, queue_id
        # might not be an ObjectID. Usually it will be, since active()
        # is a utility method, so short-circuit for performance.
        if not isinstance(queue_id, objectid.ObjectId):
            queue_id = utils.to_oid(queue_id)

        return self._list(queue_id, marker, echo, client_uuid, fields,
                          include_claimed=False)

    def claimed(self, queue_id, claim_id=None, expires=None, limit=None):
        if not isinstance(queue_id, objectid.ObjectId):
            queue_id = utils.to_oid(queue_id)

        query = {
            'c.id': claim_id,
            'c.e': {'$gt': expires or timeutils.utcnow()},
            'q': queue_id,
        }

        if not claim_id:
            # lookup over c.id to use the index
            query['c.id'] = {'$ne': None}

        msgs = self._col.find(query, sort=[('_id', 1)])

        if limit:
            msgs = msgs.limit(limit)

        now = timeutils.utcnow()

        def denormalizer(msg):
            oid = msg['_id']
            age = now - utils.oid_utc(oid)

            return {
                'id': str(oid),
                'age': age.seconds,
                'ttl': msg['t'],
                'body': msg['b'],
                'claim': msg['c']
            }

        return utils.HookedCursor(msgs, denormalizer)

    def unclaim(self, claim_id):
        try:
            cid = utils.to_oid(claim_id)
        except ValueError:
            return

        self._col.update({'c.id': cid},
                         {'$set': {'c': {'id': None, 'e': 0}}},
                         upsert=False, multi=True)

    def remove_expired(self, project=None):
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
        by the gc_threshold configuration option, which reduces the
        frequency at which the DB is locked for non-busy queues. Also,
        since .remove is run on each queue seperately, this reduces
        the duration that any given lock is held, avoiding blocking
        regular writes.
        """

        # TODO(kgriffs): Optimize first by batching the .removes, second
        # by setting a 'last inserted ID' in the queue collection for
        # each message inserted (TBD, may cause problematic side-effect),
        # and third, by changing the marker algorithm such that it no
        # longer depends on retaining the last message in the queue!
        for id in self._get_queue_ids():
            self._remove_expired(id)

    def list(self, queue, project=None, marker=None, limit=10,
             echo=False, client_uuid=None, include_claimed=False):

        if marker is not None:
            try:
                marker = int(marker)
            except ValueError:
                raise exceptions.MalformedMarker()

        qid = self._get_queue_id(queue, project)
        messages = self._list(qid, marker, echo, client_uuid,
                              include_claimed=include_claimed)

        messages = messages.limit(limit).sort('_id')
        marker_id = {}

        now = timeutils.utcnow()

        def denormalizer(msg):
            oid = msg['_id']
            age = now - utils.oid_utc(oid)
            marker_id['next'] = msg['k']

            return {
                'id': str(oid),
                'age': age.seconds,
                'ttl': msg['t'],
                'body': msg['b'],
            }

        yield utils.HookedCursor(messages, denormalizer)
        yield str(marker_id['next'])

    @utils.raises_conn_error
    def get(self, queue, message_ids, project=None):
        if isinstance(message_ids, six.string_types):
            message_ids = [message_ids]

        message_ids = [utils.to_oid(id) for id in message_ids]
        now = timeutils.utcnow()

        # Base query, always check expire time
        query = {
            'q': self._get_queue_id(queue, project),
            'e': {'$gt': now},
            '_id': {'$in': message_ids},
        }

        messages = self._col.find(query)

        def denormalizer(msg):
            oid = msg['_id']
            age = now - utils.oid_utc(oid)

            return {
                'id': str(oid),
                'age': age.seconds,
                'ttl': msg['t'],
                'body': msg['b'],
            }

        return utils.HookedCursor(messages, denormalizer)

    @utils.raises_conn_error
    def post(self, queue, messages, client_uuid, project=None):
        now = timeutils.utcnow()
        queue_id = self._get_queue_id(queue, project)

        # Set the next basis marker for the first attempt.
        next_marker = self._next_marker(queue_id)

        # Results are aggregated across all attempts
        # NOTE(kgriffs): lazy instantiation
        aggregated_results = None

        # NOTE(kgriffs): This avoids iterating over messages twice,
        # since pymongo internally will iterate over them all to
        # encode as bson before submitting to mongod. By using a
        # generator, we can produce each message only once,
        # as needed by pymongo. At the same time, each message is
        # cached in case we need to retry any of them.
        message_gen = (
            {
                't': message['ttl'],
                'q': queue_id,
                'e': now + datetime.timedelta(seconds=message['ttl']),
                'u': client_uuid,
                'c': {'id': None, 'e': now},
                'b': message['body'] if 'body' in message else {},
                'k': next_marker + index,
            }

            for index, message in enumerate(messages)
        )

        prepared_messages, cached_messages = utils.cached_gen(message_gen)

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
                    message = _('%(attempts)d attempt(s) required to post '
                                '%(num_messages)d messages to queue '
                                '%(queue_id)s')
                    message %= dict(queue_id=queue_id, attempts=attempt + 1,
                                    num_messages=len(ids))

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
                    message = _('First attempt failed while adding messages '
                                'to queue %s for current request') % queue_id

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

                # First time here, convert the deque to a list
                # to support slicing.
                if isinstance(cached_messages, collections.deque):
                    cached_messages = list(cached_messages)

                # Put the successful one's IDs into aggregated_results.
                succeeded_messages = cached_messages[:failed_index]
                succeeded_ids = [msg['_id'] for msg in succeeded_messages]

                # Results are aggregated across all attempts
                if aggregated_results is None:
                    aggregated_results = succeeded_ids
                else:
                    aggregated_results.extend(succeeded_ids)

                # Retry the remaining messages with a new sequence
                # of markers.
                prepared_messages = cached_messages[failed_index:]
                next_marker = self._next_marker(queue_id)
                for index, message in enumerate(prepared_messages):
                    message['k'] = next_marker + index

                # Chill out to avoid thrashing/thundering
                self._backoff_sleep(attempt)

            except Exception as ex:
                # TODO(kgriffs): Query the DB to get the last marker that
                # made it, and extrapolate from there to figure out what
                # needs to be retried. Definitely retry on AutoReconnect;
                # other types of errors TBD.

                LOG.exception(ex)
                raise

        message = _('Hit maximum number of attempts (%(max)s) for queue '
                    '%(id)s in project %(project)s')
        message %= dict(max=options.CFG.max_attempts, id=queue_id,
                        project=project)

        LOG.warning(message)

        succeeded_ids = map(str, aggregated_results)
        raise exceptions.MessageConflict(queue, project, succeeded_ids)

    @utils.raises_conn_error
    def delete(self, queue, message_id, project=None, claim=None):
        try:
            mid = utils.to_oid(message_id)

            query = {
                'q': self._get_queue_id(queue, project),
                '_id': mid
            }

            if claim:
                now = timeutils.utcnow()
                query['e'] = {'$gt': now}
                message = self._col.find_one(query)

                if message is None:
                    return

                cid = utils.to_oid(claim)

                if not ('c' in message and
                        message['c']['id'] == cid and
                        message['c']['e'] > now):
                    raise exceptions.ClaimNotPermitted(message_id, claim)

                self._col.remove(query['_id'], w=0)
            else:
                self._col.remove(query, w=0)
        except exceptions.QueueDoesNotExist:
            pass

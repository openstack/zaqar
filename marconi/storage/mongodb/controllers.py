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

"""Implements Mongodb storage controllers.

Field Mappings:
    In order to reduce the disk / memory space used,
    fields name will be, most of the time, the first
    letter of their long name. Fields mapping will be
    updated and documented in each class.
"""

import collections
import datetime
import time

from bson import objectid
import pymongo.errors

import marconi.openstack.common.log as logging
from marconi.openstack.common import timeutils
from marconi import storage
from marconi.storage import exceptions
from marconi.storage.mongodb import options
from marconi.storage.mongodb import utils


LOG = logging.getLogger(__name__)


class QueueController(storage.QueueBase):
    """Implements queue resource operations using MongoDB.

    Queues:
        Name         Field
        ------------------
        name        ->   n
        project     ->   p
        counter     ->   c
        metadata    ->   m

    """

    def __init__(self, *args, **kwargs):
        super(QueueController, self).__init__(*args, **kwargs)

        self._col = self.driver.db["queues"]
        # NOTE(flaper87): This creates a unique compound index for
        # project and name. Using project as the first field of the
        # index allows for querying by project and project+name.
        # This is also useful for retrieving the queues list for
        # as specific project, for example. Order Matters!
        self._col.ensure_index([("p", 1), ("n", 1)], unique=True)

    #-----------------------------------------------------------------------
    # Helpers
    #-----------------------------------------------------------------------

    def _get(self, name, project=None, fields={"m": 1, "_id": 0}):
        queue = self._col.find_one({"p": project, "n": name}, fields=fields)
        if queue is None:
            raise exceptions.QueueDoesNotExist(name, project)

        return queue

    def _get_id(self, name, project=None):
        """Just like the `get` method, but only returns the queue's id

        :returns: Queue's `ObjectId`
        """
        queue = self._get(name, project, fields=["_id"])
        return queue.get("_id")

    def _get_ids(self):
        """Returns a generator producing a list of all queue IDs."""
        cursor = self._col.find({}, fields={"_id": 1})
        return (doc["_id"] for doc in cursor)

    #-----------------------------------------------------------------------
    # Interface
    #-----------------------------------------------------------------------

    def list(self, project=None, marker=None,
             limit=10, detailed=False):
        query = {"p": project}
        if marker:
            query["n"] = {"$gt": marker}

        fields = {"n": 1, "_id": 0}
        if detailed:
            fields["m"] = 1

        cursor = self._col.find(query, fields=fields)
        cursor = cursor.limit(limit).sort("n")
        marker_name = {}

        def normalizer(records):
            for rec in records:
                queue = {"name": rec["n"]}
                marker_name["next"] = queue["name"]
                if detailed:
                    queue["metadata"] = rec["m"]
                yield queue

        yield normalizer(cursor)
        yield marker_name["next"]

    def get(self, name, project=None):
        queue = self._get(name, project)
        return queue.get("m", {})

    def upsert(self, name, metadata, project=None):
        super(QueueController, self).upsert(name, metadata, project)

        rst = self._col.update({"p": project, "n": name},
                               {"$set": {"m": metadata, "c": 1}},
                               multi=False,
                               upsert=True,
                               manipulate=False)

        return not rst["updatedExisting"]

    def delete(self, name, project=None):
        self.driver.message_controller._purge_queue(name, project)
        self._col.remove({"p": project, "n": name})

    def stats(self, name, project=None):
        queue_id = self._get_id(name, project)
        controller = self.driver.message_controller
        active = controller.active(queue_id)
        claimed = controller.claimed(queue_id)

        return {
            "actions": 0,
            "messages": {
                "claimed": claimed.count(),
                "free": active.count(),
            }
        }

    def actions(self, name, project=None, marker=None, limit=10):
        raise NotImplementedError


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
        self._col = self._db["messages"]

        # NOTE(flaper87): This index is used mostly in the
        # active method but some parts of it are used in
        # other places.
        #   * q: Mostly everywhere. It must stay at the
        #       beginning of the index.
        #   * e: Together with q is used for getting a
        #       specific message. (see `get`)
        active_fields = [
            ("q", 1),
            ("e", 1),
            ("c.e", 1),
            ("k", 1),
            ("_id", -1),
        ]

        self._col.ensure_index(active_fields,
                               name="active",
                               background=True)

        # Index used for claims
        claimed_fields = [
            ("q", 1),
            ("c.id", 1),
            ("c.e", 1),
            ("_id", -1),
        ]

        self._col.ensure_index(claimed_fields,
                               name="claimed",
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
        self._col.ensure_index([("q", 1), ("k", -1)],
                               name="queue_marker",
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

        document = self._col.find_one({"q": queue_id},
                                      sort=[("k", -1)],
                                      fields={"k": 1, "_id": 0})

        # NOTE(kgriffs): this approach is faster than using "or"
        return 1 if document is None else (document["k"] + 1)

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
            "q": queue_id,
            "e": {"$lte": timeutils.utcnow()},
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
            head = self._col.find_one({"q": queue_id},
                                      sort=[("k", -1)],
                                      fields={"_id": 1})

            if head is None:
                # Assume queue was just deleted via a parallel request
                LOG.warning(_("Queue %s is empty or missing.") % queue_id)
                return

            query = {
                "q": queue_id,
                "e": {"$lte": timeutils.utcnow()},
                "_id": {"$ne": head["_id"]}
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
            self._col.remove({"q": qid}, w=0)
        except exceptions.QueueDoesNotExist:
            pass

    #-----------------------------------------------------------------------
    # Interface
    #-----------------------------------------------------------------------

    def all(self):
        return self._col.find()

    def active(self, queue_id, marker=None, echo=False,
               client_uuid=None, fields=None):

        now = timeutils.utcnow()

        query = {
            # Messages must belong to this queue
            "q": utils.to_oid(queue_id),
            # The messages can not be expired
            "e": {"$gt": now},
            # Include messages that are part of expired claims
            "c.e": {"$lte": now},
        }

        if fields and not isinstance(fields, (dict, list)):
            raise TypeError(_("Fields must be an instance of list / dict"))

        if not echo and client_uuid:
            query["u"] = {"$ne": client_uuid}

        if marker:
            query["k"] = {"$gt": marker}

        return self._col.find(query, fields=fields)

    def claimed(self, queue_id, claim_id=None, expires=None, limit=None):
        query = {
            "c.id": claim_id,
            "c.e": {"$gt": expires or timeutils.utcnow()},
            "q": utils.to_oid(queue_id),
        }

        if not claim_id:
            # lookup over c.id to use the index
            query["c.id"] = {"$ne": None}

        msgs = self._col.find(query, sort=[("_id", 1)])

        if limit:
            msgs = msgs.limit(limit)

        now = timeutils.utcnow()

        def denormalizer(msg):
            oid = msg["_id"]
            age = now - utils.oid_utc(oid)

            return {
                "id": str(oid),
                "age": age.seconds,
                "ttl": msg["t"],
                "body": msg["b"],
                "claim": msg["c"]
            }

        return utils.HookedCursor(msgs, denormalizer)

    def unclaim(self, claim_id):
        try:
            cid = utils.to_oid(claim_id)
        except ValueError:
            return

        self._col.update({"c.id": cid},
                         {"$set": {"c": {"id": None, "e": 0}}},
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
        # by setting a "last inserted ID" in the queue collection for
        # each message inserted (TBD, may cause problematic side-effect),
        # and third, by changing the marker algorithm such that it no
        # longer depends on retaining the last message in the queue!
        for id in self._get_queue_ids():
            self._remove_expired(id)

    def list(self, queue, project=None, marker=None,
             limit=10, echo=False, client_uuid=None):

        if marker is not None:
            try:
                marker = int(marker)
            except ValueError:
                raise exceptions.MalformedMarker()

        qid = self._get_queue_id(queue, project)
        messages = self.active(qid, marker, echo, client_uuid)

        messages = messages.limit(limit).sort("_id")
        marker_id = {}

        now = timeutils.utcnow()

        def denormalizer(msg):
            oid = msg["_id"]
            age = now - utils.oid_utc(oid)
            marker_id['next'] = msg["k"]

            return {
                "id": str(oid),
                "age": age.seconds,
                "ttl": msg["t"],
                "body": msg["b"],
            }

        yield utils.HookedCursor(messages, denormalizer)
        yield str(marker_id['next'])

    def get(self, queue, message_id, project=None):
        mid = utils.to_oid(message_id)
        now = timeutils.utcnow()

        # Base query, always check expire time
        query = {
            "q": self._get_queue_id(queue, project),
            "e": {"$gt": now},
            "_id": mid
        }

        message = self._col.find_one(query)

        if message is None:
            raise exceptions.MessageDoesNotExist(message_id, queue, project)

        oid = message["_id"]
        age = now - utils.oid_utc(oid)

        return {
            "id": str(oid),
            "age": age.seconds,
            "ttl": message["t"],
            "body": message["b"],
        }

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
                "t": message["ttl"],
                "q": queue_id,
                "e": now + datetime.timedelta(seconds=message["ttl"]),
                "u": client_uuid,
                "c": {"id": None, "e": now},
                "b": message["body"] if "body" in message else {},
                "k": next_marker + index,
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

                return map(str, ids)

            except pymongo.errors.DuplicateKeyError as ex:
                # Try again with the remaining messages

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
                succeeded_ids = [msg["_id"] for msg in succeeded_messages]

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
                    message["k"] = next_marker + index

                self._backoff_sleep(attempt)

            except Exception as ex:
                # TODO(kgriffs): Query the DB to get the last marker that
                # made it, and extrapolate from there to figure out what
                # needs to be retried. Definitely retry on AutoReconnect;
                # other types of errors TBD.

                LOG.exception(ex)
                raise

        message = _("Hit maximum number of attempts (%(max)s) for queue "
                    "%(id)s in project %(project)s")
        message %= dict(max=options.CFG.max_attempts, id=queue_id,
                        project=project)

        LOG.warning(message)

        succeeded_ids = map(str, aggregated_results)
        raise exceptions.MessageConflict(queue, project, succeeded_ids)

    def delete(self, queue, message_id, project=None, claim=None):
        try:
            mid = utils.to_oid(message_id)

            query = {
                "q": self._get_queue_id(queue, project),
                "_id": mid
            }

            if claim:
                now = timeutils.utcnow()
                query["e"] = {"$gt": now}
                message = self._col.find_one(query)

                if message is None:
                    return

                cid = utils.to_oid(claim)

                if not ("c" in message and
                        message["c"]["id"] == cid and
                        message["c"]["e"] > now):
                    raise exceptions.ClaimNotPermitted(message_id, claim)

                self._col.remove(query["_id"], w=0)
            else:
                self._col.remove(query, w=0)
        except exceptions.QueueDoesNotExist:
            pass


class ClaimController(storage.ClaimBase):
    """Implements claim resource operations using MongoDB.

    No dedicated collection is being used
    for claims.

    Claims are created in the messages
    collection and live within messages, that is,
    in the c field.

    This implementation certainly uses more space
    on disk but reduces the number of queries to
    be executed and the time needed to retrieve
    claims and claimed messages.

    As for the memory usage, this implementation
    requires less memory since a single index is
    required. The index is a compound index between
    the claim id and it's expiration timestamp.
    """

    def _get_queue_id(self, queue, project):
        queue_controller = self.driver.queue_controller
        return queue_controller._get_id(queue, project)

    def get(self, queue, claim_id, project=None):
        msg_ctrl = self.driver.message_controller

        # Check whether the queue exists or not
        qid = self._get_queue_id(queue, project)

        # Base query, always check expire time
        now = timeutils.utcnow()

        try:
            cid = utils.to_oid(claim_id)
        except ValueError:
            raise exceptions.ClaimDoesNotExist()

        age = now - utils.oid_utc(cid)

        def messages(msg_iter):
            msg = msg_iter.next()
            yield msg.pop("claim")
            yield msg

            # Smoke it!
            for msg in msg_iter:
                del msg["claim"]
                yield msg

        try:
            # Lets get claim's data
            # from the first message
            # in the iterator
            messages = messages(msg_ctrl.claimed(qid, cid, now))
            claim = messages.next()
            claim = {
                "age": age.seconds,
                "ttl": claim.pop("t"),
                "id": str(claim["id"]),
            }
        except StopIteration:
            raise exceptions.ClaimDoesNotExist(cid, queue, project)

        return (claim, messages)

    def create(self, queue, metadata, project=None, limit=10):
        """Creates a claim.

        This implementation was done in a best-effort fashion.
        In order to create a claim we need to get a list
        of messages that can be claimed. Once we have that
        list we execute a query filtering by the ids returned
        by the previous query.

        Since there's a lot of space for race conditions here,
        we'll check if the number of updated records is equal to
        the max number of messages to claim. If the number of updated
        messages is lower than limit we'll try to claim the remaining
        number of messages.

        This 2 queries are required because there's no way, as for the
        time being, to executed an update on a limited number of records
        """
        msg_ctrl = self.driver.message_controller

        # We don't need the qid here but
        # we need to verify it exists.
        qid = self._get_queue_id(queue, project)

        ttl = int(metadata.get("ttl", 60))
        oid = objectid.ObjectId()

        now = timeutils.utcnow()
        ttl_delta = datetime.timedelta(seconds=ttl)
        expires = now + ttl_delta

        meta = {
            "id": oid,
            "t": ttl,
            "e": expires,
        }

        # Get a list of active, not claimed nor expired
        # messages that could be claimed.
        msgs = msg_ctrl.active(qid, fields={"_id": 1})
        msgs = msgs.limit(limit).sort("_id")

        messages = iter([])

        # Lets respect the limit
        # during the count
        if msgs.count(True) == 0:
            return (str(oid), messages)

        ids = [msg["_id"] for msg in msgs]
        now = timeutils.utcnow()

        # Set claim field for messages in ids
        updated = msg_ctrl._col.update({"_id": {"$in": ids},
                                        "$or": [
                                            {"c.id": None},
                                            {
                                                "c.id": {"$ne": None},
                                                "c.e": {"$lte": now}
                                            }
                                        ]},
                                       {"$set": {"c": meta}}, upsert=False,
                                       multi=True)["n"]

        # NOTE(flaper87): Dirty hack!
        # This sets the expiration time to
        # `expires` on messages that would
        # expire before claim.
        msg_ctrl._col.update({"q": queue,
                              "e": {"$lt": expires},
                              "c.id": oid},
                             {"$set": {"e": expires, "t": ttl}},
                             upsert=False, multi=True)

        if updated != 0:
            claim, messages = self.get(queue, oid, project=project)
        return (str(oid), messages)

    def update(self, queue, claim_id, metadata, project=None):
        try:
            cid = utils.to_oid(claim_id)
        except ValueError:
            raise exceptions.ClaimDoesNotExist(claim_id, queue, project)

        now = timeutils.utcnow()
        ttl = int(metadata.get("ttl", 60))
        ttl_delta = datetime.timedelta(seconds=ttl)

        expires = now + ttl_delta

        if now > expires:
            msg = _("New ttl will make the claim expires")
            raise ValueError(msg)

        qid = self._get_queue_id(queue, project)
        msg_ctrl = self.driver.message_controller
        claimed = msg_ctrl.claimed(qid, cid, expires=now, limit=1)

        try:
            claimed.next()
        except StopIteration:
            raise exceptions.ClaimDoesNotExist(claim_id, queue, project)

        meta = {
            "id": cid,
            "t": ttl,
            "e": expires,
        }

        msg_ctrl._col.update({"q": qid, "c.id": cid},
                             {"$set": {"c": meta}},
                             upsert=False, multi=True)

        # NOTE(flaper87): Dirty hack!
        # This sets the expiration time to
        # `expires` on messages that would
        # expire before claim.
        msg_ctrl._col.update({"q": qid,
                              "e": {"$lt": expires},
                              "c.id": cid},
                             {"$set": {"e": expires, "t": ttl}},
                             upsert=False, multi=True)

    def delete(self, queue, claim_id, project=None):
        msg_ctrl = self.driver.message_controller
        msg_ctrl.unclaim(claim_id)

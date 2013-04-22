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

"""
Mongodb storage controllers  implementation

Fields Mapping:
    In order to reduce the disk / memory space used,
    fields name will be, most of the time, the first
    letter of their long name. Fields mapping will be
    updated and documented in each class.
"""

import datetime

from bson import objectid

from marconi.openstack.common import timeutils
from marconi import storage
from marconi.storage import exceptions
from marconi.storage.mongodb import utils


class QueueController(storage.QueueBase):
    """
    Queues:
        Name       Field
        ----------------
        tenant    ->   t
        metadata  ->   m
        name      ->   n

    """

    def __init__(self, *args, **kwargs):
        super(QueueController, self).__init__(*args, **kwargs)

        self._col = self.driver.db["queues"]
        # NOTE(flaper87): This creates a unique compound index for
        # tenant and name. Using tenant as the first field of the
        # index allows for querying by tenant and tenant+name.
        # This is also useful for retrieving the queues list for
        # as specific tenant, for example. Order Matters!
        self._col.ensure_index([("t", 1), ("n", 1)], unique=True)

    def list(self, tenant=None):
        cursor = self._col.find({"t": tenant}, fields=dict(n=1, m=1, _id=0))
        for queue in cursor:
            queue["name"] = queue.pop("n")
            queue["metadata"] = queue.pop("m", {})
            yield queue

    def _get(self, name, tenant=None, fields={"m": 1, "_id": 0}):
        queue = self._col.find_one({"t": tenant, "n": name}, fields=fields)
        if queue is None:
            raise exceptions.QueueDoesNotExist(name, tenant)
        return queue

    def get_id(self, name, tenant=None):
        """
        Just like `get` method but returns the queue's id

        :returns: Queue's `ObjectId`
        """
        queue = self._get(name, tenant, fields=["_id"])
        return queue.get("_id")

    def get(self, name, tenant=None):
        queue = self._get(name, tenant)
        return queue.get("m", {})

    def upsert(self, name, metadata, tenant=None):
        super(QueueController, self).upsert(name, metadata, tenant)

        rst = self._col.update({"t": tenant, "n": name},
                               {"$set": {"m": metadata}},
                               multi=False,
                               upsert=True,
                               manipulate=False)

        return not rst["updatedExisting"]

    def delete(self, name, tenant=None):
        self.driver.message_controller.purge_queue(name, tenant)
        self._col.remove({"t": tenant, "n": name})

    def stats(self, name, tenant=None):
        qid = self.get_id(name, tenant)
        msg_ctrl = self.driver.message_controller
        active = msg_ctrl.active(qid)
        claimed = msg_ctrl.claimed(qid)

        return {
            "actions": 0,
            "messages": {
                "claimed": claimed.count(),
                "free": active.count(),
            }
        }

    def actions(self, name, tenant=None, marker=None, limit=10):
        raise NotImplementedError


class MessageController(storage.MessageBase):
    """
    Messages:
        Name       Field
        ----------------
        queue   ->   q
        expires ->   e
        ttl     ->   t
        uuid    ->   u
        claim    ->   c
    """

    def __init__(self, *args, **kwargs):
        super(MessageController, self).__init__(*args, **kwargs)
        # Make sure indexes exist before,
        # doing anything.
        self._col = self.driver.db["messages"]

        # NOTE(flaper87): Let's make sure we clean up
        # expired messages. Notice that TTL indexes run
        # a clean up thread every minute, this means that
        # every message would have an implicit 1min grace
        # if we don't filter them out in the active method.
        self._col.ensure_index("e", background=True,
                               expireAfterSeconds=0)

        # NOTE(flaper87): This index is used mostly in the
        # active method but some parts of it are used in
        # other places.
        #   * q: Mostly everywhere. It must stay at the
        #       beginning of the index.
        #   * e: Together with q is used for getting a
        #       specific message. (see `get`)
        self._col.ensure_index([("q", 1),
                                ("e", 1),
                                ("c.e", 1),
                                ("_id", -1)], background=True)

        # Indexes used for claims
        self._col.ensure_index([("q", 1),
                                ("c.id", 1),
                                ("c.e", 1),
                                ("_id", -1)], background=True)

    def _get_queue_id(self, queue, tenant):
        queue_controller = self.driver.queue_controller
        return queue_controller.get_id(queue, tenant)

    def all(self):
        return self._col.find()

    def active(self, queue, marker=None, echo=False,
               client_uuid=None, fields=None):

        now = timeutils.utcnow()

        query = {
            # Messages must belong to this queue
            "q": utils.to_oid(queue),
            "e": {"$gt": now},
            "c.e": {"$lte": now},
        }

        if fields and not isinstance(fields, (dict, list)):
            raise TypeError(_("Fields must be an instance of list / dict"))

        if not echo and client_uuid:
            query["u"] = {"$ne": client_uuid}

        if marker:
            query["_id"] = {"$gt": utils.to_oid(marker)}

        return self._col.find(query, fields=fields)

    def claimed(self, queue, claim_id=None, expires=None, limit=None):

        query = {
            "c.id": claim_id,
            "c.e": {"$gt": expires or timeutils.utcnow()},
            "q": utils.to_oid(queue),
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
        cid = utils.to_oid(claim_id)
        self._col.update({"c.id": cid},
                         {"$set": {"c": {"id": None, "e": 0}}},
                         upsert=False, multi=True)

    def list(self, queue, tenant=None, marker=None,
             limit=10, echo=False, client_uuid=None):

        qid = self._get_queue_id(queue, tenant)
        messages = self.active(qid, marker, echo, client_uuid)
        messages = messages.limit(limit).sort("_id")
        marker_id = {}

        now = timeutils.utcnow()

        def denormalizer(msg):
            oid = msg["_id"]
            age = now - utils.oid_utc(oid)
            marker_id['next'] = oid

            return {
                "id": str(oid),
                "age": age.seconds,
                "ttl": msg["t"],
                "body": msg["b"],
            }

        yield utils.HookedCursor(messages, denormalizer)
        yield str(marker_id['next'])

    def get(self, queue, message_id, tenant=None):

        # Base query, always check expire time
        mid = utils.to_oid(message_id)
        query = {
            "q": self._get_queue_id(queue, tenant),
            #"e": {"$gt": timeutils.utcnow()},
            "_id": mid
        }

        message = self._col.find_one(query)

        if message is None:
            raise exceptions.MessageDoesNotExist(mid, queue, tenant)

        oid = message["_id"]
        age = timeutils.utcnow() - utils.oid_utc(oid)

        return {
            "id": str(oid),
            "age": age.seconds,
            "ttl": message["t"],
            "body": message["b"],
        }

    def post(self, queue, messages, client_uuid, tenant=None):
        qid = self._get_queue_id(queue, tenant)

        now = timeutils.utcnow()

        def denormalizer(messages):
            for msg in messages:
                ttl = int(msg["ttl"])
                expires = now + datetime.timedelta(seconds=ttl)

                yield {
                    "t": ttl,
                    "q": qid,
                    "e": expires,
                    "u": client_uuid,
                    "c": {"id": None, "e": now},
                    "b": msg['body'] if 'body' in msg else {}
                }

        ids = self._col.insert(denormalizer(messages))
        return map(str, ids)

    def delete(self, queue, message_id, tenant=None, claim=None):
        try:
            query = {
                "q": self._get_queue_id(queue, tenant),
                "_id": utils.to_oid(message_id)
            }

            if claim:
                now = timeutils.utcnow_ts()
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

    def purge_queue(self, queue, tenant=None):
        try:
            qid = self._get_queue_id(queue, tenant)
            self._col.remove({"q": qid}, w=0)
        except exceptions.QueueDoesNotExist:
            pass


class ClaimController(storage.ClaimBase):
    """
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

    def _get_queue_id(self, queue, tenant):
        queue_controller = self.driver.queue_controller
        return queue_controller.get_id(queue, tenant)

    def get(self, queue, claim_id, tenant=None):
        msg_ctrl = self.driver.message_controller

        # Check whether the queue exists or not
        qid = self._get_queue_id(queue, tenant)

        # Base query, always check expire time
        now = timeutils.utcnow()
        cid = utils.to_oid(claim_id)
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
            raise exceptions.ClaimDoesNotExist(cid, queue, tenant)

        return (claim, messages)

    def create(self, queue, metadata, tenant=None, limit=10):
        """
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
        qid = self._get_queue_id(queue, tenant)

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
                             {"$set": {"e": expires}},
                             upsert=False, multi=True)

        if updated != 0:
            claim, messages = self.get(queue, oid, tenant=tenant)
        return (str(oid), messages)

    def update(self, queue, claim_id, metadata, tenant=None):
        cid = utils.to_oid(claim_id)
        now = timeutils.utcnow()
        ttl = int(metadata.get("ttl", 60))
        ttl_delta = datetime.timedelta(seconds=ttl)

        expires = now + ttl_delta

        if now > expires:
            msg = _("New ttl will make the claim expires")
            raise ValueError(msg)

        qid = self._get_queue_id(queue, tenant)
        msg_ctrl = self.driver.message_controller
        claimed = msg_ctrl.claimed(qid, cid, expires=now, limit=1)

        try:
            claimed.next()
        except StopIteration:
            raise exceptions.ClaimDoesNotExist(cid, queue, tenant)

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
                             {"$set": {"e": expires}},
                             upsert=False, multi=True)

    def delete(self, queue, claim_id, tenant=None):
        msg_ctrl = self.driver.message_controller
        msg_ctrl.unclaim(claim_id)

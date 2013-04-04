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
        self._col.remove({"t": tenant, "n": name})

    def stats(self, name, tenant=None):
        msg_ctrl = self.driver.message_controller
        # NOTE(flaper87): Should we split this into
        # total, active and expired ?
        msgs = msg_ctrl.active(name, tenant=tenant).count()

        return {
            "actions": 0,
            "messages": msgs
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
        self._col.ensure_index("q")
        self._col.ensure_index("u")
        self._col.ensure_index([("e", -1)])

        # Indexes used for claims
        self._col.ensure_index([("c.id", 1), ("c.e", -1)])

    def _get_queue_id(self, queue, tenant):
        queue_controller = self.driver.queue_controller
        return queue_controller.get_id(queue, tenant)

    def active(self, queue, tenant=None, marker=None,
               echo=False, client_uuid=None, fields=None):

        now = timeutils.utcnow_ts()
        query = {"$or": [
            # Get all messages that
            # haven't expired.
            {"e": {"$gt": now}},

            # Get all claimed messages which claim
            # has expired
            {"c.id": {"$ne": None}, "c.e": {"$lte": now}}
        ]}

        # Messages must belong to this queue
        query["q"] = self._get_queue_id(queue, tenant)

        if not echo and client_uuid:
            query["u"] = {"$ne": client_uuid}

        if marker:
            try:
                query["_id"] = {"$gt": utils.to_oid(marker)}
            except ValueError:
                raise StopIteration

        if fields and not isinstance(fields, (dict, list)):
            raise TypeError(_("Fields must be an instance of list / dict"))

        return self._col.find(query, fields=fields)

    def claimed(self, claim_id=None, expires=None, limit=None):

        query = {"c.id": claim_id}
        if not claim_id:
            # lookup over c.id to use the index
            query["c.id"] = {"$ne": None}
        if expires:
            query["c.e"] = {"$gt": expires}

        msgs = self._col.find(query, sort=[("_id", 1)])

        if limit:
            msgs = msgs.limit(limit)

        now = timeutils.utcnow_ts()
        for msg in msgs:
            oid = msg.get("_id")
            age = now - utils.oid_ts(oid)

            yield {
                "id": str(oid),
                "age": age,
                "ttl": msg["t"],
                "body": msg["b"],
                "claim": msg["c"]
            }

    def unclaim(self, claim_id):
        cid = utils.to_oid(claim_id)
        self._col.update({"c.id": cid},
                         {"$unset": {"c": True}},
                         upsert=False, multi=True)

    def list(self, queue, tenant=None, marker=None,
             limit=10, echo=False, client_uuid=None):

        messages = self.active(queue, tenant, marker, echo, client_uuid)
        messages = messages.limit(limit).sort("_id")

        now = timeutils.utcnow_ts()
        for msg in messages:
            oid = msg.get("_id")
            age = now - utils.oid_ts(oid)

            yield {
                "id": str(oid),
                "age": age,
                "ttl": msg["t"],
                "body": msg["b"],
                "marker": str(oid),
            }

    def get(self, queue, message_id, tenant=None):

        # Check whether the queue exists or not
        self._get_queue_id(queue, tenant)

        # Base query, always check expire time
        query = {"e": {"$gt": timeutils.utcnow_ts()}}

        mid = utils.to_oid(message_id)
        #NOTE(flaper87): Not adding the queue filter
        # since we already verified that it exists.
        # Since mid is unique, it doesn't make
        # sense to add an extra filter. This also
        # reduces index hits and query time.
        query["_id"] = mid
        message = self._col.find_one(query)

        if message is None:
            raise exceptions.MessageDoesNotExist(mid, queue, tenant)

        oid = message.get("_id")
        age = timeutils.utcnow_ts() - utils.oid_ts(oid)

        return {
            "id": oid,
            "age": age,
            "ttl": message["t"],
            "body": message["b"],
        }

    def post(self, queue, messages, tenant=None, client_uuid=None):
        qid = self._get_queue_id(queue, tenant)

        ids = []

        def denormalizer(messages):
            for msg in messages:
                ttl = int(msg["ttl"])

                oid = objectid.ObjectId()
                ids.append(str(oid))

                # Lets remove the timezone, we want it to be plain
                # utc
                expires = utils.oid_ts(oid) + ttl
                yield {
                    "_id": oid,
                    "t": ttl,
                    "q": qid,
                    "e": expires,
                    "u": client_uuid,
                    "b": msg['body'] if 'body' in msg else {}
                }

        self._col.insert(denormalizer(messages), manipulate=False)
        return ids

    def delete(self, queue, message_id, tenant=None, claim=None):
        self._get_queue_id(queue, tenant)
        mid = utils.to_oid(message_id)
        self._col.remove(mid)


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
        self._get_queue_id(queue, tenant)

        # Base query, always check expire time
        now = timeutils.utcnow_ts()
        cid = utils.to_oid(claim_id)
        age = now - utils.oid_ts(cid)

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
            messages = messages(msg_ctrl.claimed(cid, now))
            claim = messages.next()
            claim = {
                "age": age,
                "ttl": claim.pop("t"),
                "id": str(claim.pop("id")),
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
        self._get_queue_id(queue, tenant)

        ttl = int(metadata.get("ttl", 60))
        oid = objectid.ObjectId()

        # Lets remove the timezone,
        # we want it to be plain utc
        expires = utils.oid_ts(oid) + ttl

        meta = {
            "id": oid,
            "t": ttl,
            "e": expires,
        }

        # Get a list of active, not claimed nor expired
        # messages that could be claimed.
        msgs = msg_ctrl.active(queue, tenant=tenant, fields={"_id": 1})
        msgs = msgs.limit(limit).sort("_id")

        messages = iter([])

        # Lets respect the limit
        # during the count
        if msgs.count(True) == 0:
            return (str(oid), messages)

        ids = [msg["_id"] for msg in msgs]
        now = timeutils.utcnow_ts()

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

        if updated != 0:
            claim, messages = self.get(queue, oid, tenant=tenant)
        return (str(oid), messages)

    def update(self, queue, claim_id, metadata, tenant=None):
        cid = utils.to_oid(claim_id)
        now = timeutils.utcnow_ts()
        ttl = int(metadata.get("ttl", 60))

        # Lets remove the timezone,
        # we want it to be plain utc
        expires = utils.oid_ts(cid) + ttl

        if now > expires:
            msg = _("New ttl will make the claim expires")
            raise ValueError(msg)

        msg_ctrl = self.driver.message_controller
        claimed = msg_ctrl.claimed(cid, expires=now, limit=1)

        try:
            claimed.next()
        except StopIteration:
            raise exceptions.ClaimDoesNotExist(cid, queue, tenant)

        meta = {
            "id": cid,
            "t": ttl,
            "e": expires,
        }

        msg_ctrl._col.update({"c.id": cid},
                             {"$set": {"c": meta}},
                             upsert=False, multi=True)

    def delete(self, queue, claim_id, tenant=None):
        msg_ctrl = self.driver.message_controller
        msg_ctrl.unclaim(claim_id)

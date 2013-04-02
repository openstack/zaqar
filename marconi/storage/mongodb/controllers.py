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
        super(QueueController, self).delete(name, tenant)
        self._col.remove({"t": tenant, "n": name})

    def stats(self, name, tenant=None):
        raise NotImplementedError

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
    """

    def __init__(self, *args, **kwargs):
        super(MessageController, self).__init__(*args, **kwargs)
        # Make sure indexes exist before,
        # doing anything.
        self._col = self.driver.db["messages"]
        self._col.ensure_index("q", 1)
        self._col.ensure_index("u", 1)
        self._col.ensure_index([("e", -1)])

    def _get_queue_id(self, queue, tenant):
        queue_controller = self.driver.queue_controller
        return queue_controller.get_id(queue, tenant)

    def list(self, queue, tenant=None, marker=None,
             limit=10, echo=False, client_uuid=None):

        query = {"e": {"$gt": timeutils.utcnow_ts()}}
        query["q"] = self._get_queue_id(queue, tenant)

        if not echo and client_uuid:
            query["u"] = {"$ne": client_uuid}

        if marker:
            try:
                query["_id"] = {"$gt": utils.to_oid(marker)}
            except ValueError:
                raise StopIteration

        messages = self._col.find(query, limit=limit,
                                  sort=[("_id", 1)])

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

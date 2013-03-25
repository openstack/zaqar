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

from marconi import storage


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

        # NOTE(flaper87): This creates a unique compound index for
        # tenant and name. Using tenant as the first field of the
        # index allows for querying by tenant and tenant+name.
        # This is also useful for retrieving the queues list for
        # as specific tenant, for example. Order Matters!
        self._col.ensure_index([("t", 1), ("n", 1)], unique=True)

    @property
    def _col(self):
        return self.driver.db["queues"]

    def list(self, tenant=None):
        cursor = self._col.find({"t": tenant}, fields=["n", "m"])
        for queue in cursor:
            queue["name"] = queue.pop("n")
            queue["metadata"] = queue.pop("m", {})
            yield queue

    def get(self, name, tenant=None):
        queue = self._col.find_one({"t": tenant, "n": name}, fields=["m"])
        if queue is None:
            msg = (_("Queue %(name)s does not exist for tenant %(tenant)s") %
                   dict(name=name, tenant=tenant))
            raise storage.exceptions.DoesNotExist(msg)
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

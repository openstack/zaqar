# Copyright (c) 2013 Rackspace Hosting, Inc.
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

"""MongoDB storage controller for proxy partitions.

Schema:

{
    'n': Name :: str
    'h': [Host_url :: str],
    'w': Weight :: int,
}
"""

from marconi.proxy.storage import base
from marconi.proxy.storage import exceptions
from marconi.proxy.utils import round_robin
from marconi.queues.storage.mongodb import utils

PARTITIONS_INDEX = [
    ('n', 1)
]


class PartitionsController(base.PartitionsBase):
    def __init__(self, *args, **kwargs):
        super(PartitionsController, self).__init__(*args, **kwargs)

        self._col = self.driver.db['partitions']
        self._col.ensure_index(PARTITIONS_INDEX, unique=True)
        self._rr = round_robin.Selector()

    @utils.raises_conn_error
    def list(self):
        cursor = self._col.find(fields={'n': 1, 'h': 1, 'w': 1, '_id': 0})

        for entry in cursor:
            yield _normalize(entry)

    @utils.raises_conn_error
    def select(self, name):
        partition = self.get(name)
        return self._rr.next(partition['name'], partition['hosts'])

    @utils.raises_conn_error
    def get(self, name):
        fields = {'n': 1, 'w': 1, 'h': 1, '_id': 0}
        partition = self._col.find_one({'n': name},
                                       fields=fields)

        if partition is None:
            raise exceptions.PartitionNotFound(name)

        return _normalize(partition)

    @utils.raises_conn_error
    def exists(self, name):
        try:
            next(self._col.find({'n': name}))
        except StopIteration:
            return False
        else:
            return True

    @utils.raises_conn_error
    def create(self, name, weight, hosts):
        # NOTE(cpp-cabrera): overwriting behavior should be okay for
        #                    managing partitions
        self._col.update({'n': name},
                         {'$set': {'n': name, 'w': weight, 'h': hosts}},
                         upsert=True)

    @utils.raises_conn_error
    def delete(self, name):
        self._col.remove({'n': name}, w=0)


def _normalize(entry):
    return {
        'name': entry['n'],
        'hosts': entry['h'],
        'weight': entry['w']
    }

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
import six

from marconi.proxy.storage import base
from marconi.proxy.storage import exceptions
from marconi.proxy.utils import round_robin


class PartitionsController(base.PartitionsBase):
    def __init__(self, *args, **kwargs):
        super(PartitionsController, self).__init__(*args, **kwargs)

        self.driver.db['partitions'] = {}
        self._col = self.driver.db['partitions']
        self._rr = round_robin.Selector()

    def list(self):
        for entry in sorted(self._col.values(), key=lambda x: x['n']):
            yield _normalize(entry)

    def select(self, name):
        partition = self.get(name)
        return self._rr.next(partition['name'], partition['hosts'])

    def get(self, name):
        entry = None
        try:
            entry = self._col[name]
        except KeyError:
            raise exceptions.PartitionNotFound(name)

        return _normalize(entry)

    def exists(self, name):
        return self._col.get(name) is not None

    def create(self, name, weight, hosts):
        self._col[name] = {'n': name,
                           'w': weight,
                           'h': hosts}

    def delete(self, name):
        try:
            del self._col[name]
        except KeyError:
            pass


def _normalize(entry):
    return {
        'name': six.text_type(entry['n']),
        'hosts': entry['h'],
        'weight': entry['w']
    }

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


class PartitionsController(base.PartitionsBase):
    def __init__(self, *args, **kwargs):
        super(PartitionsController, self).__init__(*args, **kwargs)
        self._col = self.driver.db['partitions']

    def list(self):
        for entry in sorted(self._col.values(), key=lambda x: x['n']):
            yield _normalize(entry)

    def get(self, name):
        entry = None
        try:
            entry = self._col[name]
        except KeyError:
            raise exceptions.PartitionNotFound(name)

        return _normalize(entry)

    def exists(self, name):
        return name in self._col

    def create(self, name, weight, hosts):
        self._col[name] = {'n': name,
                           'w': weight,
                           'h': hosts}

    def delete(self, name):
        try:
            del self._col[name]
        except KeyError:
            pass

    def drop_all(self):
        self._col = {}


def _normalize(entry):
    return {
        'name': six.text_type(entry['n']),
        'hosts': entry['h'],
        'weight': entry['w']
    }

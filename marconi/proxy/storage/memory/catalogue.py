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


def _idx(project, queue):
    return project + '/' + queue


class CatalogueController(base.CatalogueBase):

    def __init__(self, *args, **kwargs):
        super(CatalogueController, self).__init__(*args, **kwargs)

        self.driver.db['catalogue'] = {}
        self._col = self.driver.db['catalogue']

    def list(self, project):
        for entry in sorted(self._col.values(), key=lambda x: x['q']):
            yield _normalize(entry)

    def get(self, project, queue):
        entry = None
        try:
            entry = self._col[_idx(project, queue)]
        except KeyError:
            raise exceptions.EntryNotFound(project, queue)

        return _normalize(entry)

    def exists(self, project, queue):
        return _idx(project, queue) in self._col

    def insert(self, project, queue, partition, host, metadata={}):
        self._col[_idx(project, queue)] = {
            'p': project, 'q': queue,
            'n': partition, 'h': host, 'm': metadata
        }

    def delete(self, project, queue):
        try:
            del self._col[_idx(project, queue)]
        except KeyError:
            pass

    def update_metadata(self, project, queue, metadata):
        try:
            self._col[_idx(project, queue)]['m'] = metadata
        except KeyError:
            pass

    def drop_all(self):
        self._col = {}


def _normalize(entry):
    return {
        'name': six.text_type(entry['q']),
        'metadata': entry['m'],
        'partition': six.text_type(entry['n']),
        'host': six.text_type(entry['h']),
    }

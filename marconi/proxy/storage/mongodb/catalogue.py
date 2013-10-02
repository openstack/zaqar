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

"""MongoDB storage controller for the proxy catalogue.

Schema:

{
    'p': Project_name :: str,
    'q': Queue_name :: str,
    'n': partition_Name :: str,
    'h': representative_Host_name :: str,
    'm': Metadata :: dict
}
"""

import marconi.openstack.common.log as logging
from marconi.proxy.storage import base
from marconi.proxy.storage import exceptions
from marconi.queues.storage.mongodb import utils

LOG = logging.getLogger(__name__)

CATALOGUE_INDEX = [
    ('p', 1),
    ('q', 1)
]


class CatalogueController(base.CatalogueBase):

    def __init__(self, *args, **kwargs):
        super(CatalogueController, self).__init__(*args, **kwargs)

        self._col = self.driver.db['catalogue']
        self._col.ensure_index(CATALOGUE_INDEX, unique=True)

    @utils.raises_conn_error
    def list(self, project, include_metadata=False):
        fields = {
            'p': 1,
            'q': 1,
            'n': 1,
            'h': 1,
            'm': 1
        }

        cursor = self._col.find({'p': project}, fields)
        for entry in cursor:
            yield _normalize(entry)

    @utils.raises_conn_error
    def get(self, project, queue):
        fields = {'p': 1, 'q': 1, 'n': 1, 'h': 1, 'm': 1, '_id': 0}
        entry = self._col.find_one({'p': project, 'q': queue},
                                   fields=fields)

        if entry is None:
            raise exceptions.EntryNotFound(project, queue)

        return _normalize(entry)

    @utils.raises_conn_error
    def exists(self, project, queue):
        return self._col.find_one({'p': project, 'q': queue}) is not None

    @utils.raises_conn_error
    def insert(self, project, queue, partition, host, metadata={}):
        self._col.insert({'p': project, 'q': queue,
                          'n': partition, 'h': host, 'm': metadata})

    @utils.raises_conn_error
    def delete(self, project, queue):
        self._col.remove({'p': project, 'q': queue}, w=0)

    @utils.raises_conn_error
    def update_metadata(self, project, queue, metadata):
        # NOTE(cpp-cabrera): since update does not create, checking
        #                    for existence isn't necesssary
        self._col.update({'p': project, 'q': queue},
                         {'$set': {'m': metadata}},
                         multi=False, manipulate=False)

    @utils.raises_conn_error
    def drop_all(self):
        self._col.drop()
        self._col.ensure_index(CATALOGUE_INDEX, unique=True)


def _normalize(entry):
    return {
        'name': entry['q'],
        'metadata': entry.get('m', {}),
        'partition': entry['n'],
        'host': entry['h']
    }

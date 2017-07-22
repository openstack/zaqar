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

"""MongoDB storage controller for the queues catalogue.

Serves to construct an association between a project + queue -> pool.

::

    {
        'p_q': project_queue :: six.text_type,
        's': pool_identifier :: six.text_type
    }
"""

from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.mongodb import utils


PRIMARY_KEY = utils.PROJ_QUEUE_KEY

CATALOGUE_INDEX = [
    (PRIMARY_KEY, 1)
]


class CatalogueController(base.CatalogueBase):

    def __init__(self, *args, **kwargs):
        super(CatalogueController, self).__init__(*args, **kwargs)

        self._col = self.driver.database.catalogue
        self._col.ensure_index(CATALOGUE_INDEX, unique=True)

    @utils.raises_conn_error
    def _insert(self, project, queue, pool, upsert):
        key = utils.scope_queue_name(queue, project)
        return self._col.update_one({PRIMARY_KEY: key},
                                    {'$set': {'s': pool}}, upsert=upsert)

    @utils.raises_conn_error
    def list(self, project):
        fields = {'_id': 0}

        query = utils.scoped_query(None, project)
        return utils.HookedCursor(self._col.find(query, fields),
                                  _normalize)

    @utils.raises_conn_error
    def get(self, project, queue):
        fields = {'_id': 0}
        key = utils.scope_queue_name(queue, project)
        entry = self._col.find_one({PRIMARY_KEY: key},
                                   projection=fields)

        if entry is None:
            raise errors.QueueNotMapped(queue, project)

        return _normalize(entry)

    @utils.raises_conn_error
    def exists(self, project, queue):
        key = utils.scope_queue_name(queue, project)
        return self._col.find_one({PRIMARY_KEY: key}) is not None

    def insert(self, project, queue, pool):
        # NOTE(cpp-cabrera): _insert handles conn_error
        self._insert(project, queue, pool, upsert=True)

    @utils.raises_conn_error
    def delete(self, project, queue):
        self._col.delete_one({
            PRIMARY_KEY: utils.scope_queue_name(queue, project)})

    def update(self, project, queue, pool=None):
        # NOTE(cpp-cabrera): _insert handles conn_error
        res = self._insert(project, queue, pool, upsert=False)

        if res.matched_count == 0:
            raise errors.QueueNotMapped(queue, project)

    @utils.raises_conn_error
    def drop_all(self):
        self._col.drop()
        self._col.ensure_index(CATALOGUE_INDEX, unique=True)


def _normalize(entry):
    project, queue = utils.parse_scoped_project_queue(entry[PRIMARY_KEY])
    return {
        'queue': queue,
        'project': project,
        'pool': entry['s']
    }

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

"""Implements the MongoDB storage controller for queues.

Field Mappings:
    In order to reduce the disk / memory space used,
    field names will be, most of the time, the first
    letter of their long name.
"""

import pymongo.errors

from marconi.common import config
import marconi.openstack.common.log as logging
from marconi.openstack.common import timeutils
from marconi.queues import storage
from marconi.queues.storage import exceptions
from marconi.queues.storage.mongodb import utils

LOG = logging.getLogger(__name__)
CFG = config.namespace('limits:storage').from_options(
    default_queue_paging=10,
)


class QueueController(storage.QueueBase):
    """Implements queue resource operations using MongoDB.

    Queues:
        Name         Field
        ------------------
        name        ->   n
        project     ->   p
        counter     ->   c
        metadata    ->   m

    """

    def __init__(self, *args, **kwargs):
        super(QueueController, self).__init__(*args, **kwargs)

        self._col = self.driver.db['queues']
        # NOTE(flaper87): This creates a unique compound index for
        # project and name. Using project as the first field of the
        # index allows for querying by project and project+name.
        # This is also useful for retrieving the queues list for
        # as specific project, for example. Order Matters!
        self._col.ensure_index([('p', 1), ('n', 1)], unique=True)

    #-----------------------------------------------------------------------
    # Helpers
    #-----------------------------------------------------------------------

    def _get(self, name, project=None, fields={'m': 1, '_id': 0}):
        queue = self._col.find_one({'p': project, 'n': name}, fields=fields)
        if queue is None:
            raise exceptions.QueueDoesNotExist(name, project)

        return queue

    def _get_np(self):
        """Returns a generator producing a list of all queue (n, p)."""
        cursor = self._col.find({}, fields={'n': 1, 'p': 1})
        return ((doc['n'], doc['p']) for doc in cursor)

    #-----------------------------------------------------------------------
    # Interface
    #-----------------------------------------------------------------------

    def list(self, project=None, marker=None,
             limit=None, detailed=False):

        if limit is None:
            limit = CFG.default_queue_paging

        query = {'p': project}
        if marker:
            query['n'] = {'$gt': marker}

        fields = {'n': 1, '_id': 0}
        if detailed:
            fields['m'] = 1

        cursor = self._col.find(query, fields=fields)
        cursor = cursor.limit(limit).sort('n')
        marker_name = {}

        def normalizer(record):
            queue = {'name': record['n']}
            marker_name['next'] = queue['name']
            if detailed:
                queue['metadata'] = record['m']
            return queue

        yield utils.HookedCursor(cursor, normalizer)
        yield marker_name and marker_name['next']

    @utils.raises_conn_error
    def get_metadata(self, name, project=None):
        queue = self._get(name, project)
        return queue.get('m', {})

    @utils.raises_conn_error
    def create(self, name, project=None):
        try:
            self._col.insert({'p': project, 'n': name, 'm': {}, 'c': 1})

        except pymongo.errors.DuplicateKeyError:
            return False
        else:
            return True

    @utils.raises_conn_error
    def exists(self, name, project=None):
        return self._col.find_one({'p': project, 'n': name}) is not None

    @utils.raises_conn_error
    def set_metadata(self, name, metadata, project=None):
        rst = self._col.update({'p': project, 'n': name},
                               {'$set': {'m': metadata}},
                               multi=False,
                               manipulate=False)

        if not rst['updatedExisting']:
            raise exceptions.QueueDoesNotExist(name, project)

    @utils.raises_conn_error
    def delete(self, name, project=None):
        self.driver.message_controller._purge_queue(name, project)
        self._col.remove({'p': project, 'n': name})

    @utils.raises_conn_error
    def stats(self, name, project=None):
        if not self.exists(name, project=project):
            raise exceptions.QueueDoesNotExist(name, project)

        controller = self.driver.message_controller

        active = controller.count(name, project=project, include_claimed=False)
        total = controller.count(name, project=project, include_claimed=True)

        message_stats = {
            'claimed': total - active,
            'free': active,
            'total': total,
        }

        try:
            oldest = controller.first(name, project=project, sort=1)
            newest = controller.first(name, project=project, sort=-1)
        except exceptions.QueueIsEmpty:
            pass
        else:
            now = timeutils.utcnow_ts()
            message_stats['oldest'] = utils.stat_message(oldest, now)
            message_stats['newest'] = utils.stat_message(newest, now)

        return {'messages': message_stats}

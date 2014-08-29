# Copyright (c) 2014 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""
Schema:
  'n': name :: six.text_type
  'p': project :: six.text_type
  's': storage pool :: six.text_type
  'c': capabilities :: dict
"""

import functools

from zaqar.queues.storage import base
from zaqar.queues.storage import errors
from zaqar.queues.storage.mongodb import utils

FLAVORS_INDEX = [
    ('p', 1),
    ('n', 1),
]

FLAVORS_STORAGE_POOL_INDEX = [
    ('s', 1)
]

# NOTE(cpp-cabrera): used for get/list operations. There's no need to
# show the marker or the _id - they're implementation details.
OMIT_FIELDS = (('_id', False),)


def _field_spec(detailed=False):
    return dict(OMIT_FIELDS + (() if detailed else (('c', False),)))


class FlavorsController(base.FlavorsBase):

    def __init__(self, *args, **kwargs):
        super(FlavorsController, self).__init__(*args, **kwargs)

        self._col = self.driver.database.flavors
        self._col.ensure_index(FLAVORS_INDEX,
                               background=True,
                               name='flavors_name',
                               unique=True)
        self._col.ensure_index(FLAVORS_STORAGE_POOL_INDEX,
                               background=True,
                               name='flavors_storage_pool_name')

        self._pools_ctrl = self.driver.pools_controller

    @utils.raises_conn_error
    def _list_by_pool(self, pool, limit=10, detailed=False):
        query = {'s': pool}
        cursor = self._col.find(query, fields=_field_spec(detailed),
                                limit=limit).sort('n', 1)

        normalizer = functools.partial(_normalize, detailed=detailed)
        return utils.HookedCursor(cursor, normalizer)

    @utils.raises_conn_error
    def list(self, project=None, marker=None, limit=10, detailed=False):
        query = {'p': project}
        if marker is not None:
            query['n'] = {'$gt': marker}

        cursor = self._col.find(query, fields=_field_spec(detailed),
                                limit=limit).sort('n', 1)

        normalizer = functools.partial(_normalize, detailed=detailed)
        return utils.HookedCursor(cursor, normalizer)

    @utils.raises_conn_error
    def get(self, name, project=None, detailed=False):
        res = self._col.find_one({'n': name, 'p': project},
                                 _field_spec(detailed))

        if not res:
            raise errors.FlavorDoesNotExist(name)

        return _normalize(res, detailed)

    @utils.raises_conn_error
    def create(self, name, pool, project=None, capabilities=None):

        # NOTE(flaper87): It's faster to call exists and raise an
        # error than calling get and letting the controller raise
        # the exception.
        if not self._pools_ctrl.exists(pool):
            raise errors.PoolDoesNotExist(pool)

        capabilities = {} if capabilities is None else capabilities
        self._col.update({'n': name, 'p': project},
                         {'$set': {'s': pool, 'c': capabilities}},
                         upsert=True)

    @utils.raises_conn_error
    def exists(self, name, project=None):
        return self._col.find_one({'n': name, 'p': project}) is not None

    @utils.raises_conn_error
    def update(self, name, project=None, pool=None, capabilities=None):
        fields = {}

        if capabilities is not None:
            fields['c'] = capabilities

        if pool is not None:
            fields['s'] = pool

        assert fields, '`pool` or `capabilities` not found in kwargs'
        res = self._col.update({'n': name, 'p': project},
                               {'$set': fields},
                               upsert=False)

        if not res['updatedExisting']:
            raise errors.FlavorDoesNotExist(name)

    @utils.raises_conn_error
    def delete(self, name, project=None):
        self._col.remove({'n': name, 'p': project}, w=0)

    @utils.raises_conn_error
    def drop_all(self):
        self._col.drop()
        self._col.ensure_index(FLAVORS_INDEX, unique=True)


def _normalize(pool, detailed=False):
    ret = {
        'name': pool['n'],
        'project': pool['p'],
        'pool': pool['s'],
    }

    if detailed:
        ret['capabilities'] = pool['c']

    return ret

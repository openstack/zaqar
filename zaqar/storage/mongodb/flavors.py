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
  's': storage pool_group :: six.text_type
  'c': capabilities :: dict
"""

import functools

from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.mongodb import utils

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
                               name='flavors_storage_pool_group_name')

        self._pools_ctrl = self.driver.pools_controller

    @utils.raises_conn_error
    def _list_by_pool_group(self, pool_group, limit=10, detailed=False):
        query = {'s': pool_group}
        cursor = self._col.find(query, projection=_field_spec(detailed),
                                limit=limit).sort('n', 1)

        normalizer = functools.partial(_normalize, detailed=detailed)
        return utils.HookedCursor(cursor, normalizer)

    @utils.raises_conn_error
    def list(self, project=None, marker=None, limit=10, detailed=False):
        query = {'p': project}
        if marker is not None:
            query['n'] = {'$gt': marker}

        cursor = self._col.find(query, projection=_field_spec(detailed),
                                limit=limit).sort('n', 1)
        marker_name = {}

        def normalizer(flavor):
            marker_name['next'] = flavor['n']
            return _normalize(flavor, detailed=detailed)

        yield utils.HookedCursor(cursor, normalizer)
        yield marker_name and marker_name['next']

    @utils.raises_conn_error
    def get(self, name, project=None, detailed=False):
        res = self._col.find_one({'n': name, 'p': project},
                                 _field_spec(detailed))

        if not res:
            raise errors.FlavorDoesNotExist(name)

        return _normalize(res, detailed)

    @utils.raises_conn_error
    def create(self, name, pool_group, project=None, capabilities=None):

        # NOTE(flaper87): Check if there are pools in this group.
        # Should there be a `group_exists` method?
        # NOTE(wanghao): Since we didn't pass the group name just pool name,
        # so we don't need to get the pool by group.
        if not list(self._pools_ctrl.get_pools_by_group(pool_group)):
            raise errors.PoolGroupDoesNotExist(pool_group)

        capabilities = {} if capabilities is None else capabilities
        self._col.update_one({'n': name, 'p': project},
                             {'$set': {'s': pool_group, 'c': capabilities}},
                             upsert=True)

    @utils.raises_conn_error
    def exists(self, name, project=None):
        return self._col.find_one({'n': name, 'p': project}) is not None

    @utils.raises_conn_error
    def update(self, name, project=None, pool_group=None, capabilities=None):
        fields = {}

        if capabilities is not None:
            fields['c'] = capabilities

        if pool_group is not None:
            fields['s'] = pool_group

        assert fields, '`pool_group` or `capabilities` not found in kwargs'
        res = self._col.update_one({'n': name, 'p': project},
                                   {'$set': fields},
                                   upsert=False)

        if res.matched_count == 0:
            raise errors.FlavorDoesNotExist(name)

    @utils.raises_conn_error
    def delete(self, name, project=None):
        self._col.delete_one({'n': name, 'p': project})

    @utils.raises_conn_error
    def drop_all(self):
        self._col.drop()
        self._col.ensure_index(FLAVORS_INDEX, unique=True)


def _normalize(flavor, detailed=False):
    ret = {
        'name': flavor['n'],
        'pool_group': flavor['s'],
    }

    if detailed:
        ret['capabilities'] = flavor['c']

    return ret

# Copyright (c) 2013 Rackspace, Inc.
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

"""pools: an implementation of the pool management storage
controller for mongodb.

Schema:
  'n': name :: six.text_type
  'u': uri :: six.text_type
  'w': weight :: int
  'o': options :: dict
"""

import functools
from pymongo import errors as mongo_error

from zaqar.common import utils as common_utils
from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.mongodb import utils

POOLS_INDEX = [
    ('n', 1)
]

URI_INDEX = [
    ('u', 1)
]

# NOTE(cpp-cabrera): used for get/list operations. There's no need to
# show the marker or the _id - they're implementation details.
OMIT_FIELDS = (('_id', False),)


def _field_spec(detailed=False):
    return dict(OMIT_FIELDS + (() if detailed else (('o', False),)))


class PoolsController(base.PoolsBase):

    def __init__(self, *args, **kwargs):
        super(PoolsController, self).__init__(*args, **kwargs)

        self._col = self.driver.database.pools
        self._col.ensure_index(POOLS_INDEX,
                               background=True,
                               name='pools_name',
                               unique=True)

        self._col.ensure_index(URI_INDEX,
                               background=True,
                               name='pools_uri',
                               unique=True)

    @utils.raises_conn_error
    def _list(self, marker=None, limit=10, detailed=False):
        query = {}
        if marker is not None:
            query['n'] = {'$gt': marker}

        cursor = self._col.find(query, projection=_field_spec(detailed),
                                limit=limit).sort('n')
        marker_name = {}

        def normalizer(pool):
            marker_name['next'] = pool['n']
            return _normalize(pool, detailed=detailed)

        yield utils.HookedCursor(cursor, normalizer)
        yield marker_name and marker_name['next']

    @utils.raises_conn_error
    def _get(self, name, detailed=False):
        res = self._col.find_one({'n': name},
                                 _field_spec(detailed))
        if not res:
            raise errors.PoolDoesNotExist(name)

        return _normalize(res, detailed)

    @utils.raises_conn_error
    def _get_pools_by_group(self, group=None, detailed=False):
        cursor = self._col.find({'g': group}, projection=_field_spec(detailed))
        normalizer = functools.partial(_normalize, detailed=detailed)
        return utils.HookedCursor(cursor, normalizer)

    @utils.raises_conn_error
    def _create(self, name, weight, uri, group=None, options=None):
        options = {} if options is None else options
        try:
            self._col.update_one({'n': name},
                                 {'$set': {'n': name,
                                           'w': weight,
                                           'u': uri,
                                           'g': group,
                                           'o': options}},
                                 upsert=True)
        except mongo_error.DuplicateKeyError:
            raise errors.PoolAlreadyExists()

    @utils.raises_conn_error
    def _exists(self, name):
        return self._col.find_one({'n': name}) is not None

    @utils.raises_conn_error
    def _update(self, name, **kwargs):
        names = ('uri', 'weight', 'group', 'options')
        fields = common_utils.fields(kwargs, names,
                                     pred=lambda x: x is not None,
                                     key_transform=lambda x: x[0])
        assert fields, ('`weight`, `uri`, `group`, '
                        'or `options` not found in kwargs')

        res = self._col.update_one({'n': name},
                                   {'$set': fields},
                                   upsert=False)
        if res.matched_count == 0:
            raise errors.PoolDoesNotExist(name)

    @utils.raises_conn_error
    def _delete(self, name):
        # NOTE(wpf): Initializing the Flavors controller here instead of
        # doing so in __init__ is required to avoid falling in a maximum
        # recursion error.
        try:
            pool = self.get(name)
            pools_group = self.get_pools_by_group(pool['group'])
            flavor_ctl = self.driver.flavors_controller
            res = list(flavor_ctl._list_by_pool_group(pool['group']))

            # NOTE(flaper87): If this is the only pool in the
            # group and it's being used by a flavor, don't allow
            # it to be deleted.
            if res and len(pools_group) == 1:
                flavors = ', '.join([x['name'] for x in res])
                raise errors.PoolInUseByFlavor(name, flavors)

            self._col.delete_one({'n': name})
        except errors.PoolDoesNotExist:
            pass

    @utils.raises_conn_error
    def _drop_all(self):
        self._col.drop()
        self._col.ensure_index(POOLS_INDEX, unique=True)


def _normalize(pool, detailed=False):
    ret = {
        'name': pool['n'],
        'group': pool['g'],
        'uri': pool['u'],
        'weight': pool['w'],
    }
    if detailed:
        ret['options'] = pool['o']

    return ret

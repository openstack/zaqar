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
  'n': name :: str
  'u': uri :: str
  'w': weight :: int
  'o': options :: dict
  'f': flavor :: str
"""

import functools
from oslo_log import log as logging
from pymongo import errors as mongo_error

from zaqar.common import utils as common_utils
from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.mongodb import utils

POOLS_INDEX = [
    ('n', 1)
]

LOG = logging.getLogger(__name__)

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
        self._col.create_index(POOLS_INDEX,
                               background=True,
                               name='pools_name',
                               unique=True)

        self._col.create_index(URI_INDEX,
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
    def _get_pools_by_flavor(self, flavor=None, detailed=False):
        query = {}
        if flavor is None:
            query = {'f': None}
        elif flavor.get('name') is not None:
            query = {'f': flavor.get('name')}
        cursor = self._col.find(query,
                                projection=_field_spec(detailed))
        ntotal = self._col.count_documents(query)
        normalizer = functools.partial(_normalize, detailed=detailed)
        return utils.HookedCursor(cursor, normalizer, ntotal=ntotal)

    @utils.raises_conn_error
    def _create(self, name, weight, uri, flavor=None,
                options=None):
        options = {} if options is None else options
        try:
            self._col.update_one({'n': name},
                                 {'$set': {'n': name,
                                           'w': weight,
                                           'u': uri,
                                           'f': flavor,
                                           'o': options}},
                                 upsert=True)
        except mongo_error.DuplicateKeyError:
            LOG.exception('Pool "%s" already exists', name)
            raise errors.PoolAlreadyExists()

    @utils.raises_conn_error
    def _exists(self, name):
        return self._col.find_one({'n': name}) is not None

    @utils.raises_conn_error
    def _update(self, name, **kwargs):
        names = ('uri', 'weight', 'flavor', 'options')
        fields = common_utils.fields(kwargs, names,
                                     pred=lambda x: x is not None,
                                     key_transform=lambda x: x[0])
        assert fields, ('`weight`, `uri`, '
                        'or `options` not found in kwargs')

        flavor = fields.get('f')
        if flavor is not None and len(flavor) == 0:
            fields['f'] = None

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
            pools_in_flavor = []
            flavor = pool.get("flavor", None)
            if flavor is not None:
                # NOTE(gengchc2): If this is the only pool in the
                # flavor and it's being used by a flavor, don't allow
                # it to be deleted.
                flavor1 = {}
                flavor1['name'] = flavor
                pools_in_flavor = self.get_pools_by_flavor(flavor=flavor1)
                if len(pools_in_flavor) == 1:
                    raise errors.PoolInUseByFlavor(name, flavor)
            self._col.delete_one({'n': name})
        except errors.PoolDoesNotExist:
            pass

    @utils.raises_conn_error
    def _drop_all(self):
        self._col.drop()
        self._col.create_index(POOLS_INDEX, unique=True)


def _normalize(pool, detailed=False):
    ret = {
        'name': pool['n'],
        'flavor': pool['f'],
        'uri': pool['u'],
        'weight': pool['w'],
    }
    if detailed:
        ret['options'] = pool['o']

    return ret

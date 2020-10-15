# Copyright (c) 2017 ZTE Corporation.
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
controller for redis.

Schema:
  'n': name :: str
  'u': uri :: str
  'w': weight :: int
  'o': options :: dict
"""

import functools
import msgpack
from oslo_log import log as logging
import redis

from zaqar.common import utils as common_utils
from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.redis import utils

LOG = logging.getLogger(__name__)


class PoolsController(base.PoolsBase):
    """Implements Pools resource operations using Redis.

    * All pool (Redis sorted set):

        Set of all pool_ids, ordered by name. Used to delete the all
        records of table pools.

        Key: pools

        +--------+-----------------------------+
        |  Id    |  Value                      |
        +========+=============================+
        |  name  |  <pool>                     |
        +--------+-----------------------------+

    * Flavor Index (Redis sorted set):

        Set of all pool_ids for the given flavor, ordered by name.

        Key: <flavor>.pools

        +--------+-----------------------------+
        |  Id    |  Value                      |
        +========+=============================+
        |  name  |  <pool>                     |
        +--------+-----------------------------+

    * Pools Information (Redis hash):

        Key: <pool>.pools

        +----------------------+---------+
        |  Name                |  Field  |
        +======================+=========+
        |  pool                |  pl     |
        +----------------------+---------+
        |  uri                 |  u      |
        +----------------------+---------+
        |  weight              |  w      |
        +----------------------+---------+
        |  options             |  o      |
        +----------------------+---------+
        |  flavor              |  f      |
        +----------------------+---------+

    """

    def __init__(self, *args, **kwargs):
        super(PoolsController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection
        self.flavor_ctl = self.driver.flavors_controller
        self._packer = msgpack.Packer(use_bin_type=True).pack
        self._unpacker = functools.partial(msgpack.unpackb)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _list(self, marker=None, limit=10, detailed=False):
        client = self._client
        set_key = utils.pools_set_key()
        marker_key = utils.pools_name_hash_key(marker)
        if marker_key:
            rank = client.zrank(set_key, marker_key)
        else:
            rank = None
        start = rank + 1 if rank is not None else 0

        cursor = (f for f in client.zrange(set_key, start,
                                           start + limit - 1))
        marker_next = {}

        def normalizer(pools):
            marker_next['next'] = pools['pl']
            return self._normalize(pools, detailed=detailed)

        yield utils.PoolsListCursor(self._client, cursor, normalizer)
        yield marker_next and marker_next['next']

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _get(self, name, detailed=False):
        pool_key = utils.pools_name_hash_key(name)
        pool = self._client.hgetall(pool_key)
        if pool is None or len(pool) == 0:
            raise errors.PoolDoesNotExist(name)

        return self._normalize(pool, detailed)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _get_pools_by_flavor(self, flavor=None, detailed=False):
        cursor = None
        if flavor is None or flavor.get('name') is None:
            set_key = utils.pools_set_key()
            cursor = (pl for pl in self._client.zrange(set_key, 0, -1))
        elif flavor.get('name') is not None:
            subset_key = utils.pools_subset_key(flavor['name'])
            cursor = (pl for pl in self._client.zrange(subset_key, 0, -1))
        if cursor is None:
            return []
        normalizer = functools.partial(self._normalize, detailed=detailed)
        return utils.PoolsListCursor(self._client, cursor, normalizer)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _create(self, name, weight, uri, group=None, flavor=None,
                options=None):

        if group is not None:
            raise errors.PoolRedisNotSupportGroup

        flavor = flavor if flavor is not None else None
        options = {} if options is None else options
        pool_key = utils.pools_name_hash_key(name)
        subset_key = utils.pools_subset_key(flavor)
        set_key = utils.pools_set_key()
        if self._exists(name):
            self._update(name, weight=weight, uri=uri,
                         flavor=flavor, options=options)
            return

        pool = {
            'pl': name,
            'u': uri,
            'w': weight,
            'o': self._packer(options),
            'f': flavor
        }
        # Pipeline ensures atomic inserts.
        with self._client.pipeline() as pipe:
            pipe.zadd(set_key, {pool_key: 1})
            if flavor is not None:
                pipe.zadd(subset_key, {pool_key: 1})
            pipe.hmset(pool_key, pool)
            pipe.execute()

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _exists(self, name):
        pool_key = utils.pools_name_hash_key(name)
        return self._client.exists(pool_key)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _update(self, name, **kwargs):
        names = ('uri', 'weight', 'flavor', 'options')
        fields = common_utils.fields(kwargs, names,
                                     pred=lambda x: x is not None,
                                     key_transform=lambda x: x[0])
        assert fields, ('`weight`, `uri`, `flavor`, '
                        'or `options` not found in kwargs')

        if 'o' in fields:
            new_options = fields.get('o', None)
            fields['o'] = self._packer(new_options)

        pool_key = utils.pools_name_hash_key(name)
        # (gengchc2): Pipeline ensures atomic inserts.
        with self._client.pipeline() as pipe:
            # (gengchc2): If flavor is changed, we need to change.pool key
            #  in pools subset.
            if 'f' in fields:
                flavor_old = self._get(name).get('flavor')
                flavor_new = fields['f']
                if flavor_old != flavor_new:
                    if flavor_new is not None:
                        new_subset_key = utils.pools_subset_key(flavor_new)
                        pipe.zadd(new_subset_key, {pool_key: 1})
                    # (gengchc2) remove pool from flavor_old.pools subset
                    if flavor_old is not None:
                        old_subset_key = utils.pools_subset_key(flavor_old)
                        pipe.zrem(old_subset_key, pool_key)
            pipe.hmset(pool_key, fields)
            pipe.execute()

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _delete(self, name):
        try:
            pool = self.get(name)
            flavor = pool.get("flavor", None)
            # NOTE(gengchc2): If this is the only pool in the
            # flavor and it's being used by a flavor, don't allow
            # it to be deleted.
            if flavor is not None:
                flavor1 = {}
                flavor1['name'] = flavor
                pools_in_flavor = list(self.get_pools_by_flavor(
                    flavor=flavor1))
                if self.flavor_ctl.exists(flavor)\
                        and len(pools_in_flavor) == 1:
                    raise errors.PoolInUseByFlavor(name, flavor)

            pool_key = utils.pools_name_hash_key(name)
            subset_key = utils.pools_subset_key(flavor)
            set_key = utils.pools_set_key()
            with self._client.pipeline() as pipe:
                if flavor is not None:
                    pipe.zrem(subset_key, pool_key)
                pipe.zrem(set_key, pool_key)
                pipe.delete(pool_key)
                pipe.execute()
        except errors.PoolDoesNotExist:
            pass

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _drop_all(self):
        poolsobj_key = self._client.keys(pattern='*pools')
        if len(poolsobj_key) == 0:
            return
        with self._client.pipeline() as pipe:
            for key in poolsobj_key:
                pipe.delete(key)
            try:
                pipe.execute()
            except redis.exceptions.ResponseError:
                return False

    def _normalize(self, pool, detailed=False):
        ret = {
            'name': pool['pl'],
            'uri': pool['u'],
            'weight': int(pool['w']),
            'flavor': pool['f']
        }
        if detailed:
            ret['options'] = self._unpacker(pool['o'])

        return ret

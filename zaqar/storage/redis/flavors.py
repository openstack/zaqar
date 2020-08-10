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

import functools

import msgpack
import redis

from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.redis import utils


class FlavorsController(base.FlavorsBase):
    """Implements flavor resource operations using Redis.

    Redis Data Structures:
    1   All flavor_ids (Redis sorted set):

        Set of all flavor_ids, ordered by name. Used to
        delete the all records of table flavors

        Key: flavors

        +--------+-----------------------------+
        |  Id    |  Value                      |
        +========+=============================+
        |  name  |  <flavor>                   |
        +--------+-----------------------------+

    2   Project Index (Redis sorted set):

        Set of all flavors for the given project, ordered by name.

        Key: <project_id>.flavors

        +--------+-----------------------------+
        |  Id    |  Value                      |
        +========+=============================+
        |  name  |  <flavor>                   |
        +--------+-----------------------------+

    3   Flavor Information (Redis hash):

        Key: <flavor_id>.flavors

        +----------------------+---------+
        |  Name                |  Field  |
        +======================+=========+
        |  flavor              |  f      |
        +----------------------+---------+
        |  project             |  p      |
        +----------------------+---------+
        |  capabilities        |  c      |
        +----------------------+---------+
    """

    def __init__(self, *args, **kwargs):
        super(FlavorsController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection
        self._packer = msgpack.Packer(use_bin_type=True).pack
        self._unpacker = functools.partial(msgpack.unpackb)

    @utils.raises_conn_error
    def list(self, project=None, marker=None, limit=10, detailed=False):
        client = self._client
        subset_key = utils.flavor_project_subset_key(project)
        marker_key = utils.flavor_name_hash_key(marker)
        if marker_key:
            rank = client.zrank(subset_key, marker_key)
        else:
            rank = None
        start = rank + 1 if rank is not None else 0

        cursor = (f for f in client.zrange(subset_key, start,
                                           start + limit - 1))
        marker_next = {}

        def normalizer(flavor):
            marker_next['next'] = flavor['f']
            return self._normalize(flavor, detailed=detailed)

        yield utils.FlavorListCursor(self._client, cursor, normalizer)
        yield marker_next and marker_next['next']

    @utils.raises_conn_error
    def get(self, name, project=None, detailed=False):
        hash_key = utils.flavor_name_hash_key(name)
        flavors = self._client.hgetall(hash_key)

        if flavors is None or len(flavors) == 0:
            raise errors.FlavorDoesNotExist(name)

        return self._normalize(flavors, detailed)

    @utils.raises_conn_error
    def create(self, name, project=None, capabilities=None):

        capabilities = {} if capabilities is None else capabilities
        subset_key = utils.flavor_project_subset_key(project)
        set_key = utils.flavor_set_key()
        hash_key = utils.flavor_name_hash_key(name)

        flavors = self._client.hgetall(hash_key)
        if len(flavors) == 0:
            flavors = {
                'f': name,
                'p': project,
                'c': self._packer(capabilities or {}),
            }
            # Pipeline ensures atomic inserts.
            with self._client.pipeline() as pipe:
                pipe.zadd(set_key, {hash_key: 1})
                pipe.zadd(subset_key, {hash_key: 1})
                pipe.hmset(hash_key, flavors)
                pipe.execute()
        else:
            with self._client.pipeline() as pipe:
                pipe.hset(hash_key, "c", self._packer(capabilities))
                pipe.hset(hash_key, "p", project)
                pipe.execute()

    @utils.raises_conn_error
    def exists(self, name, project=None):
        set_key = utils.flavor_set_key()
        hash_key = utils.flavor_name_hash_key(name)
        return self._client.zrank(set_key, hash_key) is not None

    @utils.raises_conn_error
    def update(self, name, project=None, capabilities=None):
        hash_key = utils.flavor_name_hash_key(name)
        with self._client.pipeline() as pipe:
            pipe.hset(hash_key, "c", self._packer(capabilities))
            pipe.hset(hash_key, "p", project)
            try:
                pipe.execute()
            except redis.exceptions.ResponseError:
                raise errors.FlavorDoesNotExist(name)

    @utils.raises_conn_error
    def delete(self, name, project=None):
        subset_key = utils.flavor_project_subset_key(project)
        set_key = utils.flavor_set_key()
        hash_key = utils.flavor_name_hash_key(name)
        if self._client.zrank(subset_key, hash_key) is not None:
            with self._client.pipeline() as pipe:
                pipe.zrem(set_key, hash_key)
                pipe.zrem(subset_key, hash_key)
                pipe.delete(hash_key)
                pipe.execute()

    @utils.raises_conn_error
    def drop_all(self):
        allflavor_key = self._client.keys(pattern='*flavors')
        if len(allflavor_key) == 0:
            return
        with self._client.pipeline() as pipe:
            for key in allflavor_key:
                pipe.delete(key)
            try:
                pipe.execute()
            except redis.exceptions.ResponseError:
                return False

    def _normalize(self, flavor, detailed=False):
        ret = {
            'name': flavor['f'],
        }

        if detailed:
            ret['capabilities'] = self._unpacker(flavor['c'])
        return ret

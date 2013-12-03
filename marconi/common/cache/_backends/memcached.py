# Copyright 2013 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time

import memcache
from oslo.config import cfg

from marconi.common.cache import backends


_memcache_opts = [
    cfg.ListOpt('memcached_servers',
                default=['127.0.0.1:11211'],
                help='Memcached servers or None for in process cache.'),
]


class MemcachedBackend(backends.BaseCache):

    def __init__(self, conf, group, cache_namespace):
        conf.register_opts(_memcache_opts, group=group)
        super(MemcachedBackend, self).__init__(conf, group, cache_namespace)
        self._client = None

    @property
    def _cache(self):
        if not self._client:
            self._client = memcache.Client(self.conf.memcached_servers)
        return self._client

    def _get_ttl(self, ttl):
        """Correct ttl for memcached."""

        if ttl > 2592000:
            # NOTE(flaper87): If ttl is bigger than 30 days,
            # it needs to be translated to timestamp.
            #
            # See http://code.google.com/p/memcached/wiki/FAQ
            # "You can set expire times up to 30 days in the
            # future. After that memcached interprets it as a
            # date, and will expire the item after said date.
            # This is a simple (but obscure) mechanic."
            return ttl + int(time.time())
        return ttl

    def set(self, key, value, ttl=0):
        key = self._prepare_key(key)
        return self._cache.set(key, value, self._get_ttl(ttl))

    def unset(self, key):
        self._cache.delete(self._prepare_key(key))

    def get(self, key, default=None):
        key = self._prepare_key(key)
        value = self._cache.get(key)
        return value is None and default or value

    def get_many(self, keys, default=None):
        new_keys = map(self._prepare_key, keys)
        ret = self._cache.get_multi(new_keys)

        m = dict(zip(new_keys, keys))
        for cache_key, key in m.items():
            yield (key, ret.get(cache_key, default))

    def set_many(self, data, ttl=0):
        safe_data = {}
        for key, value in data.items():
            key = self._prepare_key(key)
            safe_data[key] = value
        self._cache.set_multi(safe_data, self._get_ttl(ttl))

    def unset_many(self, keys, version=None):
        self._cache.delete_multi(map(self._prepare_key, keys))

    def incr(self, key, delta=1):
        key = self._prepare_key(key)

        try:
            if delta < 0:
                #NOTE(flaper87): memcached doesn't support a negative delta
                return self._cache.decr(key, -delta)

            return self._cache.incr(key, delta)
        except ValueError:
            return None

    def add(self, key, value, ttl=0):
        key = self._prepare_key(key)
        return self._cache.add(key, value, self._get_ttl(ttl))

    def flush(self):
        self._cache.flush_all()

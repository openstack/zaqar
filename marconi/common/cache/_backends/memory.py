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


from marconi.common.cache import backends
from marconi.openstack.common import lockutils
from marconi.openstack.common import timeutils


class MemoryBackend(backends.BaseCache):

    def __init__(self, conf, group, cache_namespace):
        super(MemoryBackend, self).__init__(conf, group, cache_namespace)
        self._cache = {}
        self._keys_expires = {}

    def set(self, key, value, ttl=0):
        key = self._prepare_key(key)
        with lockutils.lock(key):
            expires_at = 0
            if ttl != 0:
                expires_at = timeutils.utcnow_ts() + ttl

            self._cache[key] = (expires_at, value)

            if expires_at:
                self._keys_expires.setdefault(expires_at, set()).add(key)

            return True

    def get(self, key, default=None):
        key = self._prepare_key(key)
        with lockutils.lock(key):
            now = timeutils.utcnow_ts()

            try:
                timeout, value = self._cache[key]

                if timeout and now >= timeout:
                    del self._cache[key]
                    return default

                return value
            except KeyError:
                return default

    def _purge_expired(self):
        """Removes expired keys from the cache."""

        now = timeutils.utcnow_ts()
        for timeout in sorted(self._keys_expires.keys()):

            # NOTE(flaper87): If timeout is greater
            # than `now`, stop the iteration, remaining
            # keys have not expired.
            if now < timeout:
                break

            # NOTE(flaper87): Unset every key in
            # this set from the cache if its timeout
            # is equal to `timeout`. (They key might
            # have been updated)
            for subkey in self._keys_expires.pop(timeout):
                if self._cache[subkey][0] == timeout:
                    del self._cache[subkey]

    def unset(self, key):
        self._purge_expired()

        # NOTE(flaper87): Delete the key. Using pop
        # since it could have been deleted already
        self._cache.pop(self._prepare_key(key), None)

    def flush(self):
        self._cache = {}
        self._keys_expires = {}

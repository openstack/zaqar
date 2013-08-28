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

import abc


class BaseCache(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, conf, group, cache_namespace):
        self.conf = conf[group]
        self._cache_namespace = cache_namespace

    @abc.abstractmethod
    def set(self, key, value, ttl=0):
        """Sets or updates a cache entry

        :params key: Item key as string.
        :params value: Value to assign to the key. This
                       can be anything that is handled
                       by the current backend.
        :params ttl: Key's timeout in seconds.

        :returns: True if the operation succeeds.
        """

    @abc.abstractmethod
    def get(self, key, default=None):
        """Gets one item from the cache

        :params key: Key for the item to retrieve
                     from the cache.
        :params default: The default value to return.

        :returns: `key`'s value in the cache if it exists,
                  otherwise `default` should be returned.
        """

    @abc.abstractmethod
    def unset(self, key):
        """Removes an item from cache.

        :params key: The key to remove.

        :returns: The key value if there's one
        """

    def _prepare_key(self, key):
        """Prepares the key

        This method concatenates the cache_namespace
        and the key so it can be used in the cache.

        NOTE: All cache backends have to call it
        explicitly where needed.

        :param key: The key to be prefixed
        """
        if self._cache_namespace:
            return ("%(prefix)s-%(key)s" %
                    {'prefix': self._cache_namespace, 'key': key})
        return key

    def add(self, key, value, ttl=0):
        """Sets the value for a key if it doesn't exist

        :params key: Key to create as string.
        :params value: Value to assign to the key. This
                       can be anything that is handled
                       by current backend.
        :params ttl: Key's timeout in seconds.

        :returns: False if the key exists, otherwise,
                  `set`'s result will be returned.
        """

        if self.get(key) is not None:
            return False
        return self.set(key, value, ttl)

    def get_many(self, keys, default=None):
        """Gets key's value from cache

        :params keys: List of keys to retrieve.
        :params default: The default value to return
                         for each key that is not in
                         the cache.

        :returns: A  generator of (key, value)
        """
        for k in keys:
            val = self.get(k, default=default)
            if val is not None:
                yield (k, val)

    def has_key(self, key):
        """Verifies that a key exists.

        :params key: The key to verify.

        :returns: True if the key exists, otherwise
                  False.
        """
        return self.get(key) is not None

    def set_many(self, data, ttl=0):
        """Puts several items into the cache at once

        Depending on the backend, this operation may or may
        not be efficient. The default implementation calls
        set for each (key, value) pair passed, other backends
        support set_many operations as part of their protocols.

        :params data: A dictionary like {key: val} to store
                      in the cache.
        :params ttl: Key's timeout in seconds.
        """
        for key, value in data.items():
            self.set(key, value, ttl=ttl)

    def unset_many(self, keys):
        """Removes several keys from the cache at once

        :params keys: List of keys to retrieve.
        """
        for key in keys:
            self.unset(key)

    def incr(self, key, delta=1):
        """Increments the value for a key

        NOTE: This method is not synchronized because
        get and set are.

        :params key: The key for the value to be incremented
        :params delta: Number of units by which to increment
                       the value. Pass a negative number to
                       decrement the value.

        :returns: The new value
        """
        value = self.get(key)
        if value is None:
            return None
        new_value = value + delta
        self.set(key, new_value)
        return new_value

    def append(self, key, tail):
        """Appends `value` to `key`'s value.

        :params key: The key of the value to which
                     `tail` should be appended.
        :params tail: The value to append to the
                      original.

        :returns: The new value
        """
        value = self.get(key)
        if value is None:
            return None
        new_value = value + tail
        self.set(key, new_value)
        return new_value

    def flush(self):
        """Flushes all items from the cache."""

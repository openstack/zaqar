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

import functools

import msgpack
from oslo_cache import core
from oslo_log import log as logging
from oslo_serialization import jsonutils


LOG = logging.getLogger(__name__)


class TransportLog(object):
    """Standard logging for transport driver responders

    This class implements a logging decorator that the transport driver
    responders can use for standard logging
    """

    def __init__(self, resource_type):
        self.resource_type = resource_type

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # The below line takes function names like 'on_get' and 'on_patch'
            # and returns 'GET' and 'PATCH' respectively, so we do not need
            # the name of the HTTP method to be passed.
            method = func.__name__[3:].upper()
            LOG.debug(u'%(type)s %(method)s: %(arguments)s',
                      {'type': self.resource_type,
                       'method': method,
                       'arguments': jsonutils.dumps(kwargs)})
            return func(*args, **kwargs)

        return wrapper


def memoized_getattr(meth):
    """Memoizes attributes returned by __getattr__

    It can be used to remember the results from
    __getattr__ and reduce the debt of calling
    it again when the same attribute is accessed.

    This decorator memoizes attributes by setting
    them on the object itself.

    The wrapper returned by this decorator won't alter
    the returned value.

    :returns: A wrapper around the decorated method.
    """

    @functools.wraps(meth)
    def wrapper(self, method_name):
        attr = meth(self, method_name)
        setattr(self, method_name, attr)
        return attr
    return wrapper


def caches(keygen, ttl, cond=None):
    """Flags a getter method as being cached using oslo_cache.

    It is assumed that the containing class defines an attribute
    named `_cache` that is an instance of an oslo_cache backend.

    The getter should raise an exception if the value can't be
    loaded, which will skip the caching step. Otherwise, the
    getter must return a value that can be encoded with
    msgpack.

    Note that you can also flag a remover method such that it
    will purge an associated item from the cache, e.g.::

        def project_cache_key(user, project=None):
            return user + ':' + str(project)

        class Project(object):
            def __init__(self, db, cache):
                self._db = db
                self._cache = cache

            @decorators.caches(project_cache_key, 60)
            def get_project(self, user, project=None):
                return self._db.get_project(user, project)

            @get_project.purges
            def del_project(self, user, project=None):
                self._db.delete_project(user, project)

    :param keygen: A static key generator function. This function
        must accept the same arguments as the getter, sans `self`.
    :param ttl: TTL for the cache entry, in seconds.
    :param cond: Conditional for whether or not to cache the
        value. Must be a function that takes a single value, and
        returns True or False.
    """

    def purges_prop(remover):

        @functools.wraps(remover)
        def wrapper(self, *args, **kwargs):
            # First, purge from cache
            key = keygen(*args, **kwargs)
            self._cache.delete(key)

            # Remove/delete from origin
            remover(self, *args, **kwargs)

        return wrapper

    def prop(getter):

        @functools.wraps(getter)
        def wrapper(self, *args, **kwargs):
            key = keygen(*args, **kwargs)
            packed_value = self._cache.get(key, expiration_time=ttl)

            if packed_value is core.NO_VALUE:
                value = getter(self, *args, **kwargs)

                # Cache new value if desired
                if cond is None or cond(value):
                    # NOTE(kgriffs): Setting use_bin_type is essential
                    # for being able to distinguish between Unicode
                    # and binary strings when decoding; otherwise,
                    # both types are normalized to the MessagePack
                    # str format family.
                    packed_value = msgpack.packb(value, use_bin_type=True)

                    self._cache.set(key, packed_value)
            else:
                # NOTE(kgriffs): unpackb does not default to UTF-8,
                # so we have to explicitly ask for it.
                value = msgpack.unpackb(packed_value, encoding='utf-8')

            return value

        wrapper.purges = purges_prop
        return wrapper

    return prop


def lazy_property(write=False, delete=True):
    """Creates a lazy property.

    :param write: Whether this property is "writable"
    :param delete: Whether this property can be deleted.
    """

    def wrapper(fn):
        attr_name = '_lazy_' + fn.__name__

        def getter(self):
            if not hasattr(self, attr_name):
                setattr(self, attr_name, fn(self))
            return getattr(self, attr_name)

        def setter(self, value):
            setattr(self, attr_name, value)

        def deleter(self):
            delattr(self, attr_name)

        return property(fget=getter,
                        fset=write and setter,
                        fdel=delete and deleter,
                        doc=fn.__doc__)
    return wrapper


def api_version_manager(version_info):
    """Manage API versions based on their status

    This decorator disables `DEPRECATED` APIs by default unless the user
    explicitly enables it by adding it to the `enable_deprecated_api_versions`
    configuration option.

    :param version_info: Dictionary containing the API version info.
    """
    api_version = version_info['id']
    api_updated = version_info['updated']
    deprecated = version_info['status'] == 'DEPRECATED'

    def wrapper(fn):
        @functools.wraps(fn)
        def register_api(driver, conf):
            if (deprecated and
                    [api_version] not in conf.enable_deprecated_api_versions):
                return None

            if deprecated:
                LOG.warning('Enabling API version %(version)s. '
                            'This version was marked as deprecated in '
                            '%(updated)s. Using it may expose security '
                            'issues, unexpected behavior or damage your '
                            'data.', {'version': api_version,
                                      'updated': api_updated})
            return fn(driver, conf)
        return register_api
    return wrapper

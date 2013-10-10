# Copyright (c) 2013 Rackspace, Inc.
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

import abc
import six

from oslo.config import cfg

_TRANSPORT_OPTIONS = [
    cfg.StrOpt('auth_strategy', default='')
]


@six.add_metaclass(abc.ABCMeta)
class DriverBase(object):
    """Base class for Transport Drivers to document the expected interface.

    :param conf: configuration instance
    :type conf: oslo.config.cfg.CONF
    :param storage: The storage driver
    :type storage: marconi.queues.storage.base.DataDriverBase
    :param cache: caching object
    :type cache: marconi.common.cache.backends.BaseCache
    :param control: Storage driver to handle the control plane
    :type control: marconi.queues.storage.base.ControlDriverBase
    """

    def __init__(self, conf, storage, cache, control):
        self._conf = conf
        self._storage = storage
        self._cache = cache
        self._control = control

        self._conf.register_opts(_TRANSPORT_OPTIONS)

    @abc.abstractmethod
    def listen():
        """Start listening for client requests (self-hosting mode)."""
        raise NotImplementedError

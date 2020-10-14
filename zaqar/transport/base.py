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

from zaqar.conf import default
from zaqar.conf import transport


class ResourceDefaults(object):
    """Registers and exposes defaults for resource fields."""

    def __init__(self, conf):
        self._conf = conf
        self._conf.register_opts(transport.ALL_OPTS,
                                 group=transport.GROUP_NAME)
        self._defaults = self._conf[transport.GROUP_NAME]

    @property
    def message_ttl(self):
        return self._defaults.default_message_ttl

    @property
    def claim_ttl(self):
        return self._defaults.default_claim_ttl

    @property
    def claim_grace(self):
        return self._defaults.default_claim_grace

    @property
    def subscription_ttl(self):
        return self._defaults.default_subscription_ttl


class DriverBase(object, metaclass=abc.ABCMeta):
    """Base class for Transport Drivers to document the expected interface.

    :param conf: configuration instance
    :type conf: oslo_config.cfg.CONF
    :param storage: The storage driver
    :type storage: zaqar.storage.base.DataDriverBase
    :param cache: caching object
    :type cache: dogpile.cache.region.CacheRegion
    :param control: Storage driver to handle the control plane
    :type control: zaqar.storage.base.ControlDriverBase
    """

    def __init__(self, conf, storage, cache, control):
        self._conf = conf
        self._storage = storage
        self._cache = cache
        self._control = control

        self._conf.register_opts([default.auth_strategy])
        self._defaults = ResourceDefaults(self._conf)

    @abc.abstractmethod
    def listen(self):
        """Start listening for client requests (self-hosting mode)."""
        raise NotImplementedError

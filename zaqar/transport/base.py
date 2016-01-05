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

from oslo_config import cfg
import six


_GENERAL_TRANSPORT_OPTIONS = (
    cfg.StrOpt('auth_strategy', default='',
               help=('Backend to use for authentication. '
                     'For no auth, keep it empty. '
                     'Existing strategies: keystone. '
                     'See also the keystone_authtoken section below')),
)

_RESOURCE_DEFAULTS = (
    cfg.IntOpt('default_message_ttl', default=3600,
               help=('Defines how long a message will be accessible.')),
    cfg.IntOpt('default_claim_ttl', default=300,
               help=('Defines how long a message will be in claimed state.')),
    cfg.IntOpt('default_claim_grace', default=60,
               help=('Defines the message grace period in seconds.')),
    cfg.IntOpt('default_subscription_ttl', default=3600,
               help=('Defines how long a subscription will be available.')),
)

_TRANSPORT_GROUP = 'transport'


def _config_options():
    return [
        (None, _GENERAL_TRANSPORT_OPTIONS),
        (_TRANSPORT_GROUP, _RESOURCE_DEFAULTS),
    ]


class ResourceDefaults(object):
    """Registers and exposes defaults for resource fields."""

    def __init__(self, conf):
        self._conf = conf
        self._conf.register_opts(_RESOURCE_DEFAULTS, group=_TRANSPORT_GROUP)
        self._defaults = self._conf[_TRANSPORT_GROUP]

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


@six.add_metaclass(abc.ABCMeta)
class DriverBase(object):
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

        self._conf.register_opts(_GENERAL_TRANSPORT_OPTIONS)
        self._defaults = ResourceDefaults(self._conf)

    @abc.abstractmethod
    def listen(self):
        """Start listening for client requests (self-hosting mode)."""
        raise NotImplementedError

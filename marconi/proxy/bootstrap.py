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

from oslo.config import cfg
from stevedore import driver

from marconi.common.cache import cache as oslo_cache
from marconi.common import config
from marconi.common import decorators
from marconi.common import exceptions
from marconi.openstack.common import log
from marconi.proxy import transport  # NOQA


PROJECT_CFG = config.project('marconi', 'marconi-proxy')
CFG = config.namespace('proxy:drivers').from_options(
    transport='wsgi',
    storage='memory')

LOG = log.getLogger(__name__)


class Bootstrap(object):
    """Defines the Marconi proxy bootstrapper.

    The bootstrap loads up drivers per a given configuration, and
    manages their lifetimes.
    """

    def __init__(self, config_file=None, cli_args=None):
        PROJECT_CFG.load(filename=config_file, args=cli_args)
        log.setup('marconi_proxy')

    @decorators.lazy_property(write=False)
    def storage(self):
        LOG.debug(_(u'Loading Proxy Storage Driver'))
        try:
            mgr = driver.DriverManager('marconi.proxy.storage',
                                       CFG.storage,
                                       invoke_on_load=True)
            return mgr.driver
        except RuntimeError as exc:
            LOG.exception(exc)
            raise exceptions.InvalidDriver(exc)

    @decorators.lazy_property(write=False)
    def cache(self):
        LOG.debug(_(u'Loading Proxy Cache Driver'))
        try:
            mgr = oslo_cache.get_cache(cfg.CONF)
            return mgr
        except RuntimeError as exc:
            LOG.exception(exc)
            raise exceptions.InvalidDriver(exc)

    @decorators.lazy_property(write=False)
    def transport(self):
        LOG.debug(_(u'Loading Proxy Transport Driver'))
        try:
            mgr = driver.DriverManager('marconi.proxy.transport',
                                       CFG.transport,
                                       invoke_on_load=True,
                                       invoke_args=[self.storage,
                                                    self.cache])
            return mgr.driver
        except RuntimeError as exc:
            LOG.exception(exc)
            raise exceptions.InvalidDriver(exc)

    def run(self):
        self.transport.listen()

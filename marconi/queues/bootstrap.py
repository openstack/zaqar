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

from marconi.common import decorators
from marconi.common import exceptions
from marconi.openstack.common import log
from marconi.queues.storage import pipeline
from marconi.queues import transport  # NOQA


_bootstrap_options = [
    cfg.StrOpt('transport', default='wsgi',
               help='Transport driver to use'),
    cfg.StrOpt('storage', default='sqlite',
               help='Storage driver to use'),
]

CFG = cfg.CONF
CFG.register_opts(_bootstrap_options, group="queues:drivers")

LOG = log.getLogger(__name__)


class Bootstrap(object):
    """Defines the Marconi bootstrapper.

    The bootstrap loads up drivers per a given configuration, and
    manages their lifetimes.
    """

    def __init__(self, config_file=None, cli_args=None):
        default_file = None
        if config_file is not None:
            default_file = [config_file]

        CFG(project='marconi', prog='marconi-queues', args=cli_args or [],
            default_config_files=default_file)
        log.setup('marconi')

    @decorators.lazy_property(write=False)
    def storage(self):
        storage_name = CFG['queues:drivers'].storage
        LOG.debug(_(u'Loading storage driver: ') + storage_name)

        try:
            mgr = driver.DriverManager('marconi.queues.storage',
                                       storage_name,
                                       invoke_on_load=True)

            return pipeline.Driver(CFG, mgr.driver)
        except RuntimeError as exc:
            LOG.exception(exc)
            raise exceptions.InvalidDriver(exc)

    @decorators.lazy_property(write=False)
    def transport(self):
        transport_name = CFG['queues:drivers'].transport
        LOG.debug(_(u'Loading transport driver: ') + transport_name)

        try:
            mgr = driver.DriverManager('marconi.queues.transport',
                                       transport_name,
                                       invoke_on_load=True,
                                       invoke_args=[self.storage])
            return mgr.driver
        except RuntimeError as exc:
            LOG.exception(exc)
            raise exceptions.InvalidDriver(exc)

    def run(self):
        self.transport.listen()

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
from marconi.queues.storage import sharding
from marconi.queues.storage import utils as storage_utils
from marconi.queues import transport  # NOQA

LOG = log.getLogger(__name__)

_GENERAL_OPTIONS = [
    cfg.BoolOpt('sharding', default=False,
                help='Enable sharding across multiple storage backends'),
]

_DRIVER_OPTIONS = [
    cfg.StrOpt('transport', default='wsgi',
               help='Transport driver to use'),
    cfg.StrOpt('storage', default='sqlite',
               help='Storage driver to use'),
]

_DRIVER_GROUP = 'queues:drivers'


class Bootstrap(object):
    """Defines the Marconi bootstrapper.

    The bootstrap loads up drivers per a given configuration, and
    manages their lifetimes.
    """

    def __init__(self, config_file=None, cli_args=None):
        default_file = None
        if config_file is not None:
            default_file = [config_file]

        self.conf = cfg.ConfigOpts()
        self.conf.register_opts(_GENERAL_OPTIONS)
        self.conf.register_opts(_DRIVER_OPTIONS, group=_DRIVER_GROUP)
        self.driver_conf = self.conf[_DRIVER_GROUP]

        self.conf(project='marconi', prog='marconi-queues',
                  args=cli_args or [], default_config_files=default_file)

        log.setup('marconi')

    @decorators.lazy_property(write=False)
    def storage(self):
        LOG.debug(_(u'Loading storage driver'))

        if self.conf.sharding:
            LOG.debug(_(u'Storage sharding enabled'))
            storage_driver = sharding.Driver(self.conf)
        else:
            storage_driver = storage_utils.load_storage_driver(self.conf)

        LOG.debug(_(u'Loading storage pipeline'))
        return pipeline.Driver(self.conf, storage_driver)

    @decorators.lazy_property(write=False)
    def transport(self):
        transport_name = self.driver_conf.transport
        LOG.debug(_(u'Loading transport driver: ') + transport_name)

        try:
            mgr = driver.DriverManager('marconi.queues.transport',
                                       transport_name,
                                       invoke_on_load=True,
                                       invoke_args=[self.conf, self.storage])
            return mgr.driver
        except RuntimeError as exc:
            LOG.exception(exc)
            raise exceptions.InvalidDriver(exc)

    def run(self):
        self.transport.listen()

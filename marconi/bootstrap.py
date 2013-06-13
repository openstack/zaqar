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

from marconi.common import config
from marconi.common import decorators
from marconi.common import exceptions
from marconi.openstack.common import importutils
from marconi.openstack.common import log
from marconi import transport  # NOQA.


cfg_handle = config.project('marconi')
cfg = config.namespace('drivers').from_options(
    transport='marconi.transport.wsgi',
    storage='marconi.storage.sqlite')

LOG = log.getLogger(__name__)


class Bootstrap(object):
    """Defines the Marconi bootstrapper.

    The bootstrap loads up drivers per a given configuration, and
    manages their lifetimes.
    """

    def __init__(self, config_file=None, cli_args=None):
        cfg_handle.load(filename=config_file, args=cli_args)
        log.setup("marconi")

    @decorators.lazy_property(write=False)
    def storage(self):
        msg = _("Loading Storage Driver")
        LOG.debug(msg)
        storage_module = import_driver(cfg.storage)
        return storage_module.Driver()

    @decorators.lazy_property(write=False)
    def transport(self):
        msg = _("Loading Transport Driver")
        LOG.debug(msg)
        transport_module = import_driver(cfg.transport)
        return transport_module.Driver(self.storage)

    def run(self):
        self.transport.listen()


def import_driver(module_name):
    try:
        return importutils.import_module(module_name)
    except ImportError:
        raise exceptions.InvalidDriver(
            'No module named %s' % module_name)

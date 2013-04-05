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
from marconi.common import exceptions
from marconi.openstack.common import importutils


cfg_handle = config.project('marconi')
cfg = config.namespace('drivers').from_options(
    transport='marconi.transport.wsgi',
    storage='marconi.storage.sqlite')


class Bootstrap(object):
    """
    Defines the Marconi Bootstrap

    The bootstrap loads up drivers per a given configuration, and manages their
    lifetimes.
    """

    def __init__(self, config_file=None, cli_args=None):
        cfg_handle.load(filename=config_file, args=cli_args)

        self.storage_module = import_driver(cfg.storage)
        self.transport_module = import_driver(cfg.transport)

        self.storage = self.storage_module.Driver()
        self.transport = self.transport_module.Driver(
            self.storage.queue_controller,
            self.storage.message_controller,
            self.storage.claim_controller)

    def run(self):
        self.transport.listen()


def import_driver(module_name):
    try:
        return importutils.import_module(module_name)
    except ImportError:
        raise exceptions.InvalidDriver(
            'No module named %s' % module_name)

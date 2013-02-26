# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Copyright 2012 Rackspace, Inc.
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

"""Defines the Marconi Kernel

The Kernel loads up drivers per a given configuration, and manages their
lifetimes.

"""

from ConfigParser import SafeConfigParser

import marconi.transport.wsgi as wsgi
import marconi.storage.mongodb as mongodb


class Kernel(object):

    def __init__(self, config_file):
        # @todo error handling
        cfg = SafeConfigParser()
        cfg.read(config_file)

        # @todo Determine driver types from cfg
        self.storage = mongodb.Driver(cfg)
        self.transport = wsgi.Driver(self.storage, cfg)

    def run(self):
        self.transport.listen()

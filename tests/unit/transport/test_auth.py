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
"""Test Auth."""

from oslo.config import cfg

from marconi.common import config
from marconi import tests as testing
from marconi.transport import auth


class TestTransportAuth(testing.TestBase):

    def setUp(self):
        super(TestTransportAuth, self).setUp()
        self.cfg = config.project('marconi')

    def tearDown(self):
        super(TestTransportAuth, self).tearDown()
        self.cfg.conf = cfg.ConfigOpts()

    def test_configs(self):
        auth.strategy('keystone')._register_opts(self.cfg.conf)
        self.assertIn('keystone_authtoken', self.cfg.conf)
        self.assertIn('keystone_authtoken', dir(self.cfg.from_options()))

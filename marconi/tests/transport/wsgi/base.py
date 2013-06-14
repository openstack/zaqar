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
#
# See the License for the specific language governing permissions and
# limitations under the License.

from falcon import testing

import marconi
from marconi.tests import util
from marconi.tests.util import faulty_storage


class TestBase(util.TestBase):

    config_filename = None

    def setUp(self):
        super(TestBase, self).setUp()

        if self.config_filename is None:
            self.skipTest("No config specified")

        conf_file = self.conf_path(self.config_filename)
        boot = marconi.Bootstrap(conf_file)

        self.app = boot.transport.app
        self.srmock = testing.StartResponseMock()


class TestBaseFaulty(TestBase):

    def setUp(self):
        self._storage_backup = marconi.Bootstrap.storage
        faulty = faulty_storage.Driver()
        setattr(marconi.Bootstrap, "storage", faulty)
        super(TestBaseFaulty, self).setUp()

    def tearDown(self):
        setattr(marconi.Bootstrap, "storage", self._storage_backup)
        super(TestBaseFaulty, self).tearDown()

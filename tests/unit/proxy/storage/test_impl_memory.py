# Copyright (c) 2013 Rackspace Hosting, Inc.
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
from marconi.proxy.storage import memory
from marconi.proxy.storage.memory import controllers
from marconi import tests as testing

from tests.unit.proxy.storage import base


class MemoryDriverTest(testing.TestBase):

    def setUp(self):
        super(MemoryDriverTest, self).setUp()


class MemoryPartitionsTest(base.PartitionsControllerTest):

    driver_class = memory.Driver
    controller_class = controllers.PartitionsController

    def setUp(self):
        super(MemoryPartitionsTest, self).setUp()

    def tearDown(self):
        super(MemoryPartitionsTest, self).tearDown()


class MemoryCatalogueTest(base.CatalogueControllerTest):

    driver_class = memory.Driver
    controller_class = controllers.CatalogueController

    def setUp(self):
        super(MemoryCatalogueTest, self).setUp()

    def tearDown(self):
        super(MemoryCatalogueTest, self).tearDown()

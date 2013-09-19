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
import os

from marconi.proxy.storage import mongodb
from marconi.proxy.storage.mongodb import controllers
from marconi.proxy.storage.mongodb import options
from marconi import tests as testing

from tests.unit.proxy.storage import base


class MongodbDriverTest(testing.TestBase):

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance running')

        super(MongodbDriverTest, self).setUp()
        self.load_conf('wsgi_proxy_mongodb.conf')

    def test_db_instance(self):
        driver = mongodb.Driver()
        db = driver.db
        self.assertEquals(db.name, options.CFG.database)


class MongodbPartitionsTest(base.PartitionsControllerTest):

    driver_class = mongodb.Driver
    controller_class = controllers.PartitionsController

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance found running')

        super(MongodbPartitionsTest, self).setUp()
        self.load_conf('wsgi_proxy_mongodb.conf')

    def tearDown(self):
        self.controller._col.drop()
        super(MongodbPartitionsTest, self).tearDown()


class MongodbCatalogueTest(base.CatalogueControllerTest):

    driver_class = mongodb.Driver
    controller_class = controllers.CatalogueController

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance found running')

        super(MongodbCatalogueTest, self).setUp()
        self.load_conf('wsgi_proxy_mongodb.conf')

    def tearDown(self):
        self.controller._col.drop()
        super(MongodbCatalogueTest, self).tearDown()

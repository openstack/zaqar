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

import os

from marconi.common import config
from marconi.storage import mongodb
from marconi.storage.mongodb import controllers
from marconi.tests.storage import base
from marconi.tests import util as testing


cfg = config.namespace("drivers:storage:mongodb").from_options()


class MongodbDriverTest(testing.TestBase):

    def setUp(self):
        if not os.environ.get("MONGODB_TEST_LIVE"):
            self.skipTest("No MongoDB instance running")

        super(MongodbDriverTest, self).setUp()
        self.load_conf("wsgi_mongodb.conf")

    def test_db_instance(self):
        driver = mongodb.Driver()
        db = driver.db
        self.assertEquals(db.name, cfg.database)


class MongodbQueueTests(base.QueueControllerTest):

    driver_class = mongodb.Driver
    controller_class = controllers.QueueController

    def setUp(self):
        if not os.environ.get("MONGODB_TEST_LIVE"):
            self.skipTest("No MongoDB instance running")

        super(MongodbQueueTests, self).setUp()
        self.load_conf("wsgi_mongodb.conf")

    def tearDown(self):
        self.controller._col.drop()
        super(MongodbQueueTests, self).tearDown()

    def test_indexes(self):
        col = self.controller._col
        indexes = col.index_information()
        self.assertIn("t_1_n_1", indexes)


class MongodbMessageTests(base.MessageControllerTest):

    driver_class = mongodb.Driver
    controller_class = controllers.MessageController

    def setUp(self):
        if not os.environ.get("MONGODB_TEST_LIVE"):
            self.skipTest("No MongoDB instance running")

        super(MongodbMessageTests, self).setUp()
        self.load_conf("wsgi_mongodb.conf")

    def tearDown(self):
        self.controller._col.drop()
        super(MongodbMessageTests, self).tearDown()

    def test_indexes(self):
        col = self.controller._col
        indexes = col.index_information()
        self.assertIn("q_1", indexes)
        self.assertIn("e_-1", indexes)

# Copyright (c) 2013 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import uuid

from zaqar import storage
from zaqar.storage import sqlalchemy
from zaqar.storage.sqlalchemy import controllers
from zaqar.storage.sqlalchemy import tables
from zaqar.storage.sqlalchemy import utils
from zaqar import tests as testing
from zaqar.tests.unit.storage import base


class DBCreateMixin:

    def _prepare_conf(self):
        tables.metadata.create_all(self.driver.engine)


class SqlalchemyQueueTests(DBCreateMixin, base.QueueControllerTest):
    driver_class = sqlalchemy.ControlDriver
    config_file = 'wsgi_sqlalchemy.conf'
    controller_class = controllers.QueueController
    control_driver_class = sqlalchemy.ControlDriver


class SqlalchemyPoolsTest(DBCreateMixin, base.PoolsControllerTest):
    config_file = 'wsgi_sqlalchemy.conf'
    driver_class = sqlalchemy.ControlDriver
    controller_class = controllers.PoolsController
    control_driver_class = sqlalchemy.ControlDriver

    def setUp(self):
        super().setUp()
        # self.pools_controller.create(self.pool, 100, 'localhost',
        #                              group=self.pool_group, options={})

    def test_mismatching_capabilities1(self):
        # NOTE(gengchc2): This test is used for testing mismatchming
        # capabilities in pool with flavor
        with testing.expect(storage.errors.PoolCapabilitiesMismatch):
            self.pools_controller.create(str(uuid.uuid1()),
                                         100, 'redis://localhost',
                                         flavor=self.flavor,
                                         options={})


class SqlalchemyCatalogueTest(DBCreateMixin, base.CatalogueControllerTest):
    config_file = 'wsgi_sqlalchemy.conf'
    driver_class = sqlalchemy.ControlDriver
    controller_class = controllers.CatalogueController
    control_driver_class = sqlalchemy.ControlDriver


# NOTE(gengchc2): Unittest for new flavor configure scenario.
class SqlalchemyFlavorsTest1(DBCreateMixin, base.FlavorsControllerTest1):
    config_file = 'wsgi_sqlalchemy.conf'
    driver_class = sqlalchemy.ControlDriver
    controller_class = controllers.FlavorsController
    control_driver_class = sqlalchemy.ControlDriver


class MsgidTests(testing.TestBase):

    def test_encode(self):
        ids = [3, 1, 0]
        msgids = ['5c693a50', '5c693a52', '5c693a53']
        for msgid, id in zip(msgids, ids):
            self.assertEqual(msgid, utils.msgid_encode(id))

    def test_decode(self):
        msgids = ['5c693a50', '5c693a52', '5c693a53', '']
        ids = [3, 1, 0, None]
        for msgid, id in zip(msgids, ids):
            self.assertEqual(id, utils.msgid_decode(msgid))

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

import six

from zaqar.storage import sqlalchemy
from zaqar.storage.sqlalchemy import controllers
from zaqar.storage.sqlalchemy import utils
from zaqar import tests as testing
from zaqar.tests.unit.storage import base


# NOTE(flaper87): We'll need this after splitting queues
# from the data driver
class SqlalchemyQueueTests(base.QueueControllerTest):
    driver_class = sqlalchemy.ControlDriver
    controller_class = controllers.QueueController


class SqlalchemyPoolsTest(base.PoolsControllerTest):
    driver_class = sqlalchemy.ControlDriver
    controller_class = controllers.PoolsController

    def setUp(self):
        super(SqlalchemyPoolsTest, self).setUp()
        self.load_conf('wsgi_sqlalchemy.conf')

    def tearDown(self):
        super(SqlalchemyPoolsTest, self).tearDown()


class SqlalchemyCatalogueTest(base.CatalogueControllerTest):
    driver_class = sqlalchemy.ControlDriver
    controller_class = controllers.CatalogueController

    def setUp(self):
        super(SqlalchemyCatalogueTest, self).setUp()
        self.load_conf('wsgi_sqlalchemy.conf')

    def tearDown(self):
        super(SqlalchemyCatalogueTest, self).tearDown()


class MsgidTests(testing.TestBase):

    def test_encode(self):
        if six.PY2:
            ids = [3, long(1), 0]
        elif six.PY3:
            ids = [3, 1, 0]
        msgids = ['5c693a50', '5c693a52', '5c693a53']
        for msgid, id in zip(msgids, ids):
            self.assertEqual(msgid, utils.msgid_encode(id))

    def test_decode(self):
        msgids = ['5c693a50', '5c693a52', '5c693a53', '']
        ids = [3, 1, 0, None]
        for msgid, id in zip(msgids, ids):
            self.assertEqual(id, utils.msgid_decode(msgid))

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

import datetime

import sqlalchemy as sa

from marconi.queues.storage import errors
from marconi.queues.storage import pooling
from marconi.queues.storage import sqlalchemy
from marconi.queues.storage.sqlalchemy import controllers
from marconi.queues.storage.sqlalchemy import tables
from marconi.queues.storage.sqlalchemy import utils
from marconi import tests as testing
from marconi.tests.queues.storage import base


class SqlalchemyTableTests(testing.TestBase):

    def setUp(self):
        super(SqlalchemyTableTests, self).setUp()
        self.engine = sa.create_engine('sqlite:///:memory:')
        tables.metadata.create_all(self.engine, checkfirst=True)

    def test_table_queries(self):
        self.engine.execute(tables.Queues.insert(), id=1, project='test',
                            name='marconi', metadata=utils.json_encode('aaaa'))
        self.engine.execute(tables.Messages.insert(), id=1, qid=1, ttl=10,
                            body=utils.json_encode('bbbb'), client='a',
                            created=datetime.datetime.now())
        self.engine.execute(tables.Claims.insert(), id=1, qid=1, ttl=10,
                            created=datetime.datetime.now())

        rs = self.engine.execute(tables.Claims.select())
        row = rs.fetchone()

        self.assertEqual(row.id, 1)
        self.assertEqual(row.qid, 1)
        self.assertEqual(row.ttl, 10)

        self.engine.execute(tables.Claims.delete(tables.Claims.c.id == 1))
        rs = self.engine.execute(tables.Claims.select())
        row = rs.fetchone()

        self.assertIsNone(row)


class SqlalchemyQueueTests(base.QueueControllerTest):
    driver_class = sqlalchemy.DataDriver
    controller_class = controllers.QueueController


class SqlalchemyMessageTests(base.MessageControllerTest):
    driver_class = sqlalchemy.DataDriver
    controller_class = controllers.MessageController

    def test_empty_queue_exception(self):
        queue_name = 'empty-queue-test'
        self.queue_controller.create(queue_name, None)

        self.assertRaises(errors.QueueIsEmpty,
                          self.controller.first,
                          queue_name, None, sort=1)

    def test_pop_message(self):
        queue_name = 'pop-message-test'
        self.queue_controller.create(queue_name, self.project)
        messages = [
            {
                'ttl': 60,
                'body': {
                    'event': 'BackupStarted',
                    'backupId': 'c378813c-3f0b-11e2-ad92-7823d2b0f3ce',
                },
            },
            {
                'ttl': 60,
                'body': {
                    'event': 'BackupStarted',
                    'backupId': 'd378813c-3f0b-11e2-ad92-7823d2b0f3ce',
                },
            },
            {
                'ttl': 60,
                'body': {
                    'event': 'BackupStarted',
                    'backupId': 'e378813c-3f0b-11e2-ad92-7823d2b0f3ce',
                },
            },
        ]
        uuid = '33a7ce80-0892-11e4-9d5d-28cfe91478b9'
        self.controller.post(queue_name, messages, uuid,
                             self.project)

        # Test Message Pop
        message_popped = self.controller.pop(queue_name,
                                             limit=1,
                                             project=self.project)
        self.assertEqual(len(message_popped), 1)


class SqlalchemyClaimTests(base.ClaimControllerTest):
    driver_class = sqlalchemy.DataDriver
    controller_class = controllers.ClaimController


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


class PooledMessageTests(base.MessageControllerTest):
    config_file = 'wsgi_sqlalchemy_pooled.conf'
    controller_class = pooling.MessageController
    driver_class = pooling.DataDriver
    control_driver_class = sqlalchemy.ControlDriver
    controller_base_class = pooling.RoutingController


class PooledClaimsTests(base.ClaimControllerTest):
    config_file = 'wsgi_sqlalchemy_pooled.conf'
    controller_class = pooling.ClaimController
    driver_class = pooling.DataDriver
    control_driver_class = sqlalchemy.ControlDriver
    controller_base_class = pooling.RoutingController


class PooledQueueTests(base.QueueControllerTest):
    config_file = 'wsgi_sqlalchemy_pooled.conf'
    controller_class = pooling.QueueController
    driver_class = pooling.DataDriver
    control_driver_class = sqlalchemy.ControlDriver
    controller_base_class = pooling.RoutingController

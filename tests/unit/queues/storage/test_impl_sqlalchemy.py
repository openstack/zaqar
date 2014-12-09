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
import uuid

import six
import sqlalchemy as sa
from sqlalchemy.sql import func as sfunc

from zaqar.storage import pooling
from zaqar.storage import sqlalchemy
from zaqar.storage.sqlalchemy import controllers
from zaqar.storage.sqlalchemy import tables
from zaqar.storage.sqlalchemy import utils
from zaqar import tests as testing
from zaqar.tests.queues.storage import base


class SqlalchemyTableTests(testing.TestBase):

    def setUp(self):
        super(SqlalchemyTableTests, self).setUp()
        self.engine = sa.create_engine('sqlite:///:memory:')
        tables.metadata.create_all(self.engine, checkfirst=True)

    def test_table_queries(self):
        self.engine.execute(tables.Queues.insert(), id=1, project='test',
                            name='zaqar', metadata=utils.json_encode('aaaa'))
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

    def test_expired_messages_be_deleted(self):
        messages = [{'body': 3.14, 'ttl': 0}, {'body': 0.618, 'ttl': 600}]
        client_uuid = uuid.uuid4()

        [msgid_expired, msgid] = self.controller.post(self.queue_name,
                                                      messages,
                                                      project=self.project,
                                                      client_uuid=client_uuid)
        mid = utils.msgid_decode(msgid_expired)

        def _get(count=False):
            j = sa.join(tables.Messages, tables.Queues,
                        tables.Messages.c.qid == tables.Queues.c.id)

            sel = sa.sql.select([tables.Messages.c.body,
                                tables.Messages.c.ttl,
                                tables.Messages.c.created])

            if count:
                sel = sa.sql.select([sfunc.count(tables.Messages.c.id)])

            sel = sel.select_from(j)
            and_stmt = [tables.Messages.c.id == mid,
                        tables.Queues.c.name == self.queue_name,
                        tables.Queues.c.project == self.project]

            sel = sel.where(sa.and_(*and_stmt))

            return self.driver.get(sel)

        [count] = _get(count=True)
        self.assertEqual(count, 1)

        # Expired messages will be removed from db until next Post
        message = [{'body': 3.14, 'ttl': 300}]
        self.controller.post(self.queue_name,
                             message,
                             project=self.project,
                             client_uuid=client_uuid)

        with testing.expect(utils.NoResult):
            _get()


class SqlalchemyClaimTests(base.ClaimControllerTest):
    driver_class = sqlalchemy.DataDriver
    controller_class = controllers.ClaimController

    def test_delete_message_expired_claim(self):
        # NOTE(flaper87): Several reasons to do this:
        # The sqla driver is deprecated
        # It's not optimized
        # mocking utcnow mocks the driver too, which
        # requires to put sleeps in the test
        self.skip("Fix sqlalchemy driver")


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

    def test_delete_message_expired_claim(self):
        # NOTE(flaper87): Several reasons to do this:
        # The sqla driver is deprecated
        # It's not optimized
        # mocking utcnow mocks the driver too, which
        # requires to put sleeps in the test
        self.skip("Fix sqlalchemy driver")


class PooledQueueTests(base.QueueControllerTest):
    config_file = 'wsgi_sqlalchemy_pooled.conf'
    controller_class = pooling.QueueController
    driver_class = pooling.DataDriver
    control_driver_class = sqlalchemy.ControlDriver
    controller_base_class = pooling.RoutingController


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

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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime

import sqlalchemy as sa

from marconi.queues.storage.sqlalchemy import tables
from marconi import tests as testing


class SqlalchemyTableTests(testing.TestBase):

    def setUp(self):
        super(SqlalchemyTableTests, self).setUp()
        self.engine = sa.create_engine('sqlite:///:memory:')
        tables.metadata.create_all(self.engine, checkfirst=True)

    def test_table_queries(self):
        self.engine.execute(tables.Queues.insert(), id=1, project='test',
                            name='marconi', metadata='aaaa')
        self.engine.execute(tables.Messages.insert(), id=1, qid=1, ttl=10,
                            body='bbbb', client='a',
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

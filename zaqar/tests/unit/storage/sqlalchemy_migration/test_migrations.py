# Copyright 2014 OpenStack Foundation
# Copyright 2014 Mirantis Inc
# Copyright 2016 Catalyst IT Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Tests for database migrations.

For the opportunistic testing you need to set up a db named 'openstack_citest'
with user 'openstack_citest' and password 'openstack_citest' on localhost.
The test will then use that db and u/p combo to run the tests.

For postgres on Ubuntu this can be done with the following commands:

sudo -u postgres psql
postgres=# create user openstack_citest with createdb login password
      'openstack_citest';
postgres=# create database openstack_citest with owner openstack_citest;

"""

from oslo_db.sqlalchemy import test_base
from oslo_db.sqlalchemy import utils as db_utils

from zaqar.tests.unit.storage.sqlalchemy_migration import \
    test_migrations_base as base


class ZaqarMigrationsCheckers(object):

    def assertColumnExists(self, engine, table, column):
        t = db_utils.get_table(engine, table)
        self.assertIn(column, t.c)

    def assertColumnsExist(self, engine, table, columns):
        for column in columns:
            self.assertColumnExists(engine, table, column)

    def assertColumnType(self, engine, table, column, column_type):
        t = db_utils.get_table(engine, table)
        column_ref_type = str(t.c[column].type)
        self.assertEqual(column_ref_type, column_type)

    def assertColumnCount(self, engine, table, columns):
        t = db_utils.get_table(engine, table)
        self.assertEqual(len(columns), len(t.columns))

    def assertColumnNotExists(self, engine, table, column):
        t = db_utils.get_table(engine, table)
        self.assertNotIn(column, t.c)

    def assertIndexExists(self, engine, table, index):
        t = db_utils.get_table(engine, table)
        index_names = [idx.name for idx in t.indexes]
        self.assertIn(index, index_names)

    def assertIndexMembers(self, engine, table, index, members):
        self.assertIndexExists(engine, table, index)

        t = db_utils.get_table(engine, table)
        index_columns = None
        for idx in t.indexes:
            if idx.name == index:
                index_columns = idx.columns.keys()
                break

        self.assertEqual(sorted(members), sorted(index_columns))

    def test_walk_versions(self):
        self.walk_versions(self.engine)

    def _pre_upgrade_001(self, engine):
        # Anything returned from this method will be
        # passed to corresponding _check_xxx method as 'data'.
        pass

    def _check_001(self, engine, data):
        queues_columns = [
            'id',
            'name',
            'project',
            'metadata'
        ]
        self.assertColumnsExist(
            engine, 'Queues', queues_columns)
        self.assertColumnCount(
            engine, 'Queues', queues_columns)

        poolgroup_columns = [
            'name',
        ]
        self.assertColumnsExist(
            engine, 'PoolGroup', poolgroup_columns)
        self.assertColumnCount(
            engine, 'PoolGroup', poolgroup_columns)

        pools_columns = [
            'name',
            'group',
            'uri',
            'weight',
            'options',
        ]
        self.assertColumnsExist(
            engine, 'Pools', pools_columns)
        self.assertColumnCount(
            engine, 'Pools', pools_columns)

        flavors_columns = [
            'name',
            'project',
            'pool_group',
            'capabilities',
        ]
        self.assertColumnsExist(
            engine, 'Flavors', flavors_columns)
        self.assertColumnCount(
            engine, 'Flavors', flavors_columns)

        catalogue_columns = [
            'pool',
            'project',
            'queue',
        ]
        self.assertColumnsExist(
            engine, 'Catalogue', catalogue_columns)
        self.assertColumnCount(
            engine, 'Catalogue', catalogue_columns)

        self._data_001(engine, data)

    def _data_001(self, engine, data):
        project = 'myproject'
        t = db_utils.get_table(engine, 'Queues')
        engine.execute(t.insert(), id='123', name='name', project='myproject',
                       metadata={})
        new_project = engine.execute(t.select()).fetchone().project
        self.assertEqual(project, new_project)
        engine.execute(t.delete())

    def _check_002(self, engine, data):
        # currently, 002 is just a placeholder
        pass

    def _check_003(self, engine, data):
        # currently, 003 is just a placeholder
        pass

    def _check_004(self, engine, data):
        # currently, 004 is just a placeholder
        pass

    def _check_005(self, engine, data):
        # currently, 005 is just a placeholder
        pass


class TestMigrationsMySQL(ZaqarMigrationsCheckers,
                          base.BaseWalkMigrationTestCase,
                          base.TestModelsMigrationsSync,
                          test_base.MySQLOpportunisticTestCase):
    pass

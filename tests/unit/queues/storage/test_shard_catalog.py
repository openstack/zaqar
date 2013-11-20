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

import uuid

from oslo.config import cfg

from marconi.queues.storage import sharding
from marconi.queues.storage import sqlite
from marconi.queues.storage import utils
from marconi import tests as testing


# TODO(cpp-cabrera): it would be wonderful to refactor this unit test
# so that it could use multiple control storage backends once those
# have shards/catalogue implementations.
class TestShardCatalog(testing.TestBase):

    @testing.requires_mongodb
    def setUp(self):
        super(TestShardCatalog, self).setUp()
        conf = self.load_conf('wsgi_mongodb_sharded.conf')

        conf.register_opts([cfg.StrOpt('storage')],
                           group='queues:drivers')
        control = utils.load_storage_driver(conf, control_mode=True)
        self.catalogue_ctrl = control.catalogue_controller
        self.shards_ctrl = control.shards_controller

        # NOTE(cpp-cabrera): populate catalogue
        self.shard = str(uuid.uuid1())
        self.queue = str(uuid.uuid1())
        self.project = str(uuid.uuid1())
        self.shards_ctrl.create(self.shard, 100, 'sqlite://memory')
        self.catalogue_ctrl.insert(self.project, self.queue, self.shard)
        self.catalog = sharding.Catalog(conf, control)

    def tearDown(self):
        self.catalogue_ctrl.drop_all()
        self.shards_ctrl.drop_all()
        super(TestShardCatalog, self).tearDown()

    def test_lookup_loads_correct_driver(self):
        storage = self.catalog.lookup(self.queue, self.project)
        self.assertIsInstance(storage, sqlite.DataDriver)

    def test_lookup_returns_none_if_queue_not_mapped(self):
        self.assertIsNone(self.catalog.lookup('not', 'mapped'))

    def test_lookup_returns_none_if_entry_deregistered(self):
        self.catalog.deregister(self.queue, self.project)
        self.assertIsNone(self.catalog.lookup(self.queue, self.project))

    def test_register_leads_to_successful_lookup(self):
        self.catalog.register('not_yet', 'mapped')
        storage = self.catalog.lookup('not_yet', 'mapped')
        self.assertIsInstance(storage, sqlite.DataDriver)

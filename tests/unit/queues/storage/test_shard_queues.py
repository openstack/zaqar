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

import random
import uuid

from oslo.config import cfg

from marconi.common.cache import cache as oslo_cache
from marconi.queues.storage import sharding
from marconi.queues.storage import utils
from marconi import tests as testing


@testing.requires_mongodb
class ShardQueuesTest(testing.TestBase):

    def setUp(self):
        super(ShardQueuesTest, self).setUp()
        conf = self.load_conf('wsgi_mongodb_sharded.conf')

        conf.register_opts([cfg.StrOpt('storage')],
                           group='drivers')

        cache = oslo_cache.get_cache(self.conf)
        control = utils.load_storage_driver(conf, cache, control_mode=True)
        self.shards_ctrl = control.shards_controller
        self.driver = sharding.DataDriver(conf, cache, control)
        self.controller = self.driver.queue_controller

        # fake two shards
        for _ in xrange(2):
            self.shards_ctrl.create(str(uuid.uuid1()), 100, 'sqlite://memory')

    def tearDown(self):
        self.shards_ctrl.drop_all()
        super(ShardQueuesTest, self).tearDown()

    def test_health(self):
        health = self.driver.is_alive()
        self.assertTrue(health)

    def test_listing(self):
        project = "I.G"

        interaction = self.controller.list(project=project,
                                           detailed=False)
        queues = list(next(interaction))

        self.assertEqual(len(queues), 0)

        for n in xrange(10):
            name = 'queue_%d' % n
            self.controller.create(name, project=project)
            self.controller.set_metadata(name,
                                         metadata=random.getrandbits(12),
                                         project=project)

        interaction = self.controller.list(project=project,
                                           detailed=True,
                                           limit=7)
        queues.extend(next(interaction))
        marker = next(interaction)

        self.assertEqual(len(queues), 7)

        interaction = self.controller.list(project=project,
                                           detailed=True,
                                           limit=7,
                                           marker=marker)
        queues.extend(next(interaction))

        self.assertEqual(len(queues), 10)

        # ordered by name as a whole
        self.assertTrue(all(queues[i]['name'] <= queues[i + 1]['name']
                            for i in xrange(len(queues) - 1)))

        for n in xrange(10):
            self.controller.delete('queue_%d' % n, project=project)

        interaction = self.controller.list(project=project,
                                           detailed=False)
        queues = list(next(interaction))

        self.assertEqual(len(queues), 0)

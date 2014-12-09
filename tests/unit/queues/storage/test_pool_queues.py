# Copyright (c) 2013 Rackspace, Inc.
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

import random
import uuid

from oslo.config import cfg
import six

from zaqar.openstack.common.cache import cache as oslo_cache
from zaqar.storage import pooling
from zaqar.storage import utils
from zaqar import tests as testing


@testing.requires_mongodb
class PoolQueuesTest(testing.TestBase):

    config_file = 'wsgi_mongodb_pooled.conf'

    def setUp(self):
        super(PoolQueuesTest, self).setUp()

        self.conf.register_opts([cfg.StrOpt('storage')],
                                group='drivers')

        cache = oslo_cache.get_cache()
        control = utils.load_storage_driver(self.conf, cache,
                                            control_mode=True)
        self.pools_ctrl = control.pools_controller
        self.driver = pooling.DataDriver(self.conf, cache, control)
        self.controller = self.driver.queue_controller

        # fake two pools
        for _ in six.moves.xrange(2):
            self.pools_ctrl.create(str(uuid.uuid1()), 100,
                                   'sqlite://:memory:')

    def tearDown(self):
        self.pools_ctrl.drop_all()
        super(PoolQueuesTest, self).tearDown()

    def test_ping(self):
        ping = self.driver.is_alive()
        self.assertTrue(ping)

    def test_listing(self):
        project = "I.G"

        interaction = self.controller.list(project=project,
                                           detailed=False)
        queues = list(next(interaction))

        self.assertEqual(len(queues), 0)

        for n in six.moves.xrange(10):
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
                            for i in six.moves.xrange(len(queues) - 1)))

        for n in six.moves.xrange(10):
            self.controller.delete('queue_%d' % n, project=project)

        interaction = self.controller.list(project=project,
                                           detailed=False)
        queues = list(next(interaction))

        self.assertEqual(len(queues), 0)

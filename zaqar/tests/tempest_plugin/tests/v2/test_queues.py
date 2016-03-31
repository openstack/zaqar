# Copyright (c) 2016 HuaWei, Inc.
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


from six import moves
from tempest.common.utils import data_utils
from tempest.lib import decorators
from testtools import matchers

from zaqar.tests.tempest_plugin.tests import base


class TestQueues(base.BaseV11MessagingTest):

    @decorators.idempotent_id('f2db96f3-fa02-426a-9b42-5806e12f14d4')
    def test_create_delete_queue(self):
        # Create & Delete Queue
        queue_name = data_utils.rand_name('test')
        _, body = self.create_queue(queue_name)

        self.addCleanup(self.client.delete_queue, queue_name)
        # NOTE(gmann): create_queue returns response status code as 201
        # so specifically checking the expected empty response body as
        # this is not going to be checked in response_checker().
        self.assertEqual('', body)

        self.delete_queue(queue_name)
        # lazy queue
        self.client.show_queue(queue_name)


class TestManageQueue(base.BaseV2MessagingTest):

    @classmethod
    def resource_setup(cls):
        super(TestManageQueue, cls).resource_setup()
        cls.queues = list()
        for _ in moves.xrange(5):
            queue_name = data_utils.rand_name('Queues-Test')
            cls.queues.append(queue_name)
            # Create Queue
            cls.client.create_queue(queue_name)

    @decorators.idempotent_id('8f1fec00-54fc-48b9-aa67-c10a824b768d')
    def test_list_queues(self):
        # Listing queues
        _, body = self.list_queues()
        self.assertEqual(len(body['queues']), len(self.queues))
        for item in body['queues']:
            self.assertIn(item['name'], self.queues)

    @decorators.idempotent_id('e96466e7-d43f-48f9-bfe8-59e3d40f6868')
    def test_get_queue_stats(self):
        # Retrieve random queue
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        # Get Queue Stats for a newly created Queue
        _, body = self.get_queue_stats(queue_name)
        msgs = body['messages']
        for element in ('free', 'claimed', 'total'):
            self.assertEqual(0, msgs[element])
        for element in ('oldest', 'newest'):
            self.assertNotIn(element, msgs)

    @decorators.skip_because(bug='1543900')
    @decorators.idempotent_id('dfb1e0b0-b481-4e2a-91ae-2c28b65e9c28')
    def test_set_and_get_queue_metadata(self):
        # Retrieve random queue
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        # Check the Queue has no metadata
        _, body = self.get_queue_metadata(queue_name)
        self.assertThat(body, matchers.HasLength(0))
        # Create metadata
        key3 = [0, 1, 2, 3, 4]
        key2 = data_utils.rand_name('value')
        req_body1 = dict()
        req_body1[data_utils.rand_name('key3')] = key3
        req_body1[data_utils.rand_name('key2')] = key2
        req_body = dict()
        req_body[data_utils.rand_name('key1')] = req_body1
        # Set Queue Metadata
        self.set_queue_metadata(queue_name, req_body)

        # Get Queue Metadata
        _, body = self.get_queue_metadata(queue_name)
        self.assertThat(body, matchers.Equals(req_body))

    @classmethod
    def resource_cleanup(cls):
        for queue_name in cls.queues:
            cls.client.delete_queue(queue_name)
        super(TestManageQueue, cls).resource_cleanup()

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
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from testtools import matchers

from zaqar.tests.tempest_plugin.tests import base

CONF = config.CONF


class TestQueues(base.BaseV2MessagingTest):

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

    def _post_messages(self, repeat=CONF.messaging.max_messages_per_page,
                       queue_name=None):
        message_body = self.generate_message_body(repeat=repeat)
        resp, body = self.post_messages(queue_name=queue_name,
                                        rbody=message_body)
        return resp, body

    def _create_subscriptions(self, queue_name):
        bodys = self.generate_subscription_body()
        results = []
        for body in bodys:
            resp, body = self.create_subscription(queue_name=queue_name,
                                                  rbody=body)
            results.append((resp, body))
        return results

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

    @decorators.idempotent_id('dfb1e0b0-b481-4e2a-91ae-2c28b65e9c28')
    def test_set_and_get_queue_metadata(self):
        QueueName = "QueueWithMeta"
        self.client.create_queue(QueueName)
        _, body = self.get_queue_metadata(QueueName)
        self.assertThat(body, matchers.HasLength(2))
        self.assertEqual(262144, body['_max_messages_post_size'])
        self.assertEqual(3600, body['_default_message_ttl'])
        # Create metadata
        op1 = {"op": "add",
               "path": "/metadata/_max_claim_count", "value": 2}
        op2 = {"op": "add",
               "path": "/metadata/_dead_letter_queue_messages_ttl",
               "value": 7799}
        metadata = [op1, op2]
        # Set Queue Metadata
        self.set_queue_metadata(QueueName, metadata)
        # Get Queue Metadata
        _, body = self.get_queue_metadata(QueueName)
        self.assertThat(body, matchers.HasLength(4))
        self.assertEqual(262144, body['_max_messages_post_size'])
        self.assertEqual(7799, body['_dead_letter_queue_messages_ttl'])
        self.assertEqual(2, body['_max_claim_count'])
        self.assertEqual(3600, body['_default_message_ttl'])
        self.client.delete_queue(QueueName)

    @decorators.idempotent_id('2fb6e5a8-c18f-4407-9ee7-7a13c8e09f69')
    def test_purge_queue(self):
        queue_name = self.queues[0]
        # The queue contains no messages and subscriptions by default.
        resp, body = self.list_messages(queue_name=queue_name)
        self.assertEqual([], body['messages'])
        resp, body = self.list_subscription(queue_name)
        self.assertEqual([], body['subscriptions'])
        # Post some messages and create some subscriptions for the queue.
        self._post_messages(queue_name=queue_name)
        self._create_subscriptions(queue_name=queue_name)
        # The queue contains messages and subscriptions now.
        resp, body = self.list_messages(queue_name=queue_name)
        self.assertIsNotNone(len(body['messages']))
        resp, body = self.list_subscription(queue_name)
        self.assertIsNotNone(len(body['subscriptions']))
        # Purge the queue
        resp, body = self.purge_queue(queue_name)
        self.assertEqual(204, resp.status)
        # The queue contains nothing.
        resp, body = self.list_messages(queue_name=queue_name)
        self.assertEqual([], body['messages'])
        resp, body = self.list_subscription(queue_name)
        self.assertEqual([], body['subscriptions'])

    @classmethod
    def resource_cleanup(cls):
        for queue_name in cls.queues:
            cls.client.delete_queue(queue_name)
        super(TestManageQueue, cls).resource_cleanup()

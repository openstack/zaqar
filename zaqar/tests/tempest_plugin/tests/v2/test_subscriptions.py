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

import json

from oslo_utils import uuidutils
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import decorators

from zaqar.tests.tempest_plugin.tests import base


class TestSubscriptions(base.BaseV2MessagingTest):

    @classmethod
    def resource_setup(cls):
        super(TestSubscriptions, cls).resource_setup()
        cls.queue_name = data_utils.rand_name('Queues-Test')
        # Create Queue
        cls.client.create_queue(cls.queue_name)

    def _create_subscriptions(self):
        bodys = self.generate_subscription_body()
        results = []
        for body in bodys:
            resp, body = self.create_subscription(queue_name=self.queue_name,
                                                  rbody=body)
            results.append((resp, body))
        return results

    @decorators.idempotent_id('425d5afb-31d8-40ea-a23a-ef3f5554f7cc')
    def test_create_delete_subscriptions(self):
        # create all kinds of subscriptions
        results = self._create_subscriptions()
        # delete them
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.idempotent_id('a8776d93-895f-4947-a6b0-d0da50bfd5e8')
    def test_list_subscriptions(self):
        # create all kinds of subscriptions
        results = self._create_subscriptions()
        # list them
        resp, body = self.list_subscription(self.queue_name)
        self.assertEqual('200', resp['status'])
        self.assertEqual(3, len(body['subscriptions']))
        # delete them
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.idempotent_id('de3d4a35-c5de-4f40-b6ad-7df187bf3831')
    def test_show_subscriptions(self):
        # create all kinds of subscriptions
        results = self._create_subscriptions()
        # get the first one
        subscription_id = results[0][1]["subscription_id"]
        resp, body = self.show_subscription(self.queue_name, subscription_id)
        self.assertEqual('200', resp['status'])
        self.assertEqual('http://fake:8080', body['subscriber'])
        # delete them
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.idempotent_id('90489fa2-893d-4062-b2bd-29bdd06f54f3')
    def test_update_subscriptions(self):
        # create all kinds of subscriptions
        results = self._create_subscriptions()
        # update the first one
        subscription_id = results[0][1]["subscription_id"]
        rbody = {'options': {'test': 'updated'}}
        self.update_subscription(self.queue_name, subscription_id, rbody)
        # get the new one
        resp, body = self.show_subscription(self.queue_name, subscription_id)
        self.assertEqual('200', resp['status'])
        self.assertEqual(rbody['options'], body['options'])
        # delete them
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.idempotent_id('fe0d8ec1-1a64-4490-8869-e821b2252e74')
    def test_create_subscriptions_with_duplicate_subscriber(self):
        # Adding subscriptions to the queue
        results = self._create_subscriptions()
        s_id1 = results[0][1]['subscription_id']

        # Adding a subscription with duplicate subscriber, it will reconfirm
        # the subscription and run well.
        rbody = {'subscriber': 'http://fake:8080',
                 'options': {'MessagingKeyMsg': 'MessagingValueMsg'},
                 'ttl': 293305}
        resp, body = self.create_subscription(self.queue_name, rbody)
        s_id2 = body['subscription_id']

        self.assertEqual('201', resp['status'])
        self.assertEqual(s_id2, s_id1)

        # Delete the subscriptions created
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.idempotent_id('ff4344b4-ba78-44c5-9ffc-44e53e484f76')
    def test_trust_subscription(self):
        sub_queue = data_utils.rand_name('Queues-Test')
        self.addCleanup(self.client.delete_queue, sub_queue)
        subscriber = 'trust+{0}/{1}/queues/{2}/messages'.format(
            self.client.base_url, self.client.uri_prefix, sub_queue)
        post_body = json.dumps(
            {'messages': [{'body': '$zaqar_message$', 'ttl': 60}]})
        post_headers = {'X-Project-ID': self.client.tenant_id,
                        'Client-ID': uuidutils.generate_uuid()}
        sub_body = {'ttl': 1200, 'subscriber': subscriber,
                    'options': {'post_data': post_body,
                                'post_headers': post_headers}}

        self.create_subscription(queue_name=self.queue_name, rbody=sub_body)
        message_body = self.generate_message_body()
        self.post_messages(queue_name=self.queue_name, rbody=message_body)

        if not test_utils.call_until_true(
                lambda: self.list_messages(sub_queue)[1]['messages'], 10, 1):
            self.fail("Couldn't get messages")
        _, body = self.list_messages(sub_queue)
        expected = message_body['messages'][0]
        expected['queue_name'] = self.queue_name
        expected['Message_Type'] = 'Notification'
        for message in body['messages']:
            # There are two message in the queue. One is the confirm message,
            # the other one is the notification.
            if message['body']['Message_Type'] == 'Notification':
                self.assertEqual(expected, message['body'])

    @classmethod
    def resource_cleanup(cls):
        cls.delete_queue(cls.queue_name)
        super(TestSubscriptions, cls).resource_cleanup()

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


from tempest.common.utils import data_utils
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

    @classmethod
    def resource_cleanup(cls):
        cls.delete_queue(cls.queue_name)
        super(TestSubscriptions, cls).resource_cleanup()

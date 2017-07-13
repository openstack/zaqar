# Copyright (c) 2016 LARSEN & TOUBRO LIMITED. All rights reserved.
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

from oslo_utils import uuidutils

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from zaqar.tests.tempest_plugin.tests import base

CONF = config.CONF


class TestSubscriptionsNegative(base.BaseV2MessagingTest):

    @classmethod
    def resource_setup(cls):
        super(TestSubscriptionsNegative, cls).resource_setup()
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

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('0bda2907-a783-4614-af16-23d7a7d53b72')
    def test_create_subscriptions_with_invalid_body(self):
        # Missing subscriber parameter in body
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)
        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        option_body = {key: value}
        rbody = {'options': option_body, 'ttl': message_ttl}
        self.assertRaises(lib_exc.BadRequest,
                          self.create_subscription, self.queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('36601d23-77d5-42b1-b234-6789acdda7ba')
    def test_create_subscriptions_with_no_body(self):
        # Missing parameters in body
        rbody = {}
        self.assertRaises(lib_exc.BadRequest,
                          self.create_subscription, self.queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('1d510d93-635f-4161-b071-91f838d6907e')
    def test_create_subscriptions_with_invalid_subscriber(self):
        # The subscriber type of subscription must be supported in the list
        # ['http', 'https', 'mailto']
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)
        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        option_body = {key: value}
        subscriber = 'fake'
        rbody = {'options': option_body, 'ttl': message_ttl,
                 'subscriber': subscriber}
        self.assertRaises(lib_exc.BadRequest,
                          self.create_subscription, self.queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('65be33a4-a063-47e1-b56b-9d7aa979bbcb')
    def test_create_subscriptions_with_unsupported_subscriber(self):
        # The subscriber type of subscription must be supported in the list
        # ['http', 'https', 'mailto']
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)
        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        option_body = {key: value}
        subscriber = 'email://fake'
        rbody = {'options': option_body, 'ttl': message_ttl,
                 'subscriber': subscriber}
        self.assertRaises(lib_exc.BadRequest,
                          self.create_subscription, self.queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('cada6c25-0f59-4021-a4c3-961945913998')
    def test_create_subscriptions_with_invalid_options(self):
        # Options must be a dict
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)
        option_body = '123'
        subscriber = 'http://fake:8080'
        rbody = {'options': option_body, 'ttl': message_ttl,
                 'subscriber': subscriber}
        self.assertRaises(lib_exc.BadRequest,
                          self.create_subscription, self.queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('84c1e298-c632-4ccb-859f-afe9a390081c')
    def test_create_subscriptions_with_non_integer_value_for_ttl(self):
        # The subscriber type of subscription must be supported in the list
        # ['http', 'https', 'mailto']
        message_ttl = "123"
        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        option_body = {key: value}
        subscriber = 'http://fake:8080'
        rbody = {'options': option_body, 'ttl': message_ttl,
                 'subscriber': subscriber}
        self.assertRaises(lib_exc.BadRequest,
                          self.create_subscription, self.queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('1302e137-4db6-48ad-b779-ef2095198bc2')
    def test_create_a_subscription_without_a_token(self):
        # X-Auth-Token is not provided
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)
        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        option_body = {key: value}
        subscriber = 'http://fake:8080'
        rbody = {'options': option_body, 'ttl': message_ttl,
                 'subscriber': subscriber}

        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.create_subscription, self.queue_name, rbody)

    # List Subscriptions

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('e2109835-34ad-4f0a-8bbb-43d475d1315d')
    def test_list_subscriptions_from_non_existing_queue(self):
        # Request for listing subscriptions from a non existent queue
        non_existent_queue = data_utils.rand_name('rand_queuename')
        resp, _ = self.client.list_subscription(non_existent_queue)
        self.assertEqual('200', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('95d7c77f-4912-49ce-9f38-cfcc6d5cd65b')
    def test_list_subscriptions_from_queue_with_no_subsciptions(self):
        # Request to list subscription
        resp, _ = self.client.list_subscription(self.queue_name)
        self.assertEqual('200', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('72f8c0b7-23d8-40ef-ae7c-212cc0751946')
    def test_list_subscription_without_a_token(self):
        # X-Auth-Token is not provided
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.list_subscription, self.queue_name)

    # Show Subscriptions

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('7ecc2cb9-a0f4-4d03-b903-ecf2917fda13')
    def test_show_subscriptions_from_non_existing_queue(self):
        # Show subscription details from a non existent queue
        non_existent_queue = data_utils.rand_name('rand_queuename')
        invalid_id = '123'
        self.assertRaises(lib_exc.NotFound,
                          self.show_subscription, non_existent_queue,
                          invalid_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('bb46d838-e9f9-4851-a788-c30bff41c484')
    def test_show_subscriptions_with_invalid_id(self):
        # Show subscription details with invaild id
        invalid_id = '123'
        self.assertRaises(lib_exc.NotFound,
                          self.show_subscription, self.queue_name, invalid_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('1120f006-397a-4e8b-9e79-e2dc96b37d46')
    def test_show_subscriptions_after_deleting_subscription(self):
        # Create subscription
        results = self._create_subscriptions()
        subscription_id = results[0][1]["subscription_id"]
        # Delete subscription
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)
        # Show the details of the subscription
        self.assertRaises(lib_exc.NotFound,
                          self.show_subscription, self.queue_name,
                          subscription_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('47a3f29f-6ddb-4cf2-87ed-a2b97733f386')
    def test_show_subscription_without_a_token(self):
        # X-Auth-Token is not provided
        results = self._create_subscriptions()
        subscription_id = results[0][1]["subscription_id"]
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.show_subscription, self.queue_name,
                          subscription_id)
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    # Update Subscriptions

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('5c93b468-cb84-424f-af35-d4f5febc7c56')
    def test_update_subscription_on_non_existing_queue(self):
        # Update subscription on a non existing queue
        results = self._create_subscriptions()
        subscription_id = results[0][1]["subscription_id"]
        non_existent_queue = data_utils.rand_name('rand_queuename')
        update_rbody = {'ttl': 1000}
        self.assertRaises(lib_exc.NotFound, self.client.update_subscription,
                          non_existent_queue, subscription_id, update_rbody)

        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('b383a29a-08f1-418f-8adb-c29ef080358c')
    def test_update_subscription_with_invalid_id(self):
        # Update subscription using invalid id
        results = self._create_subscriptions()
        subscription_id = uuidutils.generate_uuid()
        update_rbody = {'ttl': 100}
        self.assertRaises(lib_exc.NotFound,
                          self.client.update_subscription, self.queue_name,
                          subscription_id, update_rbody)
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('4e446118-fa90-4f67-9a91-e157fbaa5a4c')
    def test_update_subscription_with_empty_body(self):
        # Update subscription with no body
        results = self._create_subscriptions()
        subscription_id = results[0][1]["subscription_id"]
        update_rbody = {' '}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_subscription, self.queue_name,
                          subscription_id, update_rbody)
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('966f5356-9d0b-46c6-9d57-26bcd9d8e699')
    def test_update_subscription_with_invalid_TTL(self):
        # Update subscription using invalid TTL
        results = self._create_subscriptions()
        subscription_id = results[0][1]["subscription_id"]
        update_rbody = {'ttl': 50}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_subscription, self.queue_name,
                          subscription_id, update_rbody)
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('8838f3b2-d4c3-42e2-840c-4314e334a2f0')
    def test_update_subscription_with_invalid_json_in_request_body(self):
        # Update subscription with invalid json
        results = self._create_subscriptions()
        subscription_id = results[0][1]["subscription_id"]
        update_rbody = {"123"}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_subscription, self.queue_name,
                          subscription_id, update_rbody)
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('8bfe5638-0126-483e-b88a-2767fa6564e6')
    def test_update_subscription_with_invalid_token(self):
        # X-Auth-Token is not provided
        results = self._create_subscriptions()
        subscription_id = results[0][1]["subscription_id"]
        update_rbody = {"ttl": "1000"}
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.update_subscription, self.queue_name,
                          subscription_id, update_rbody)
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    # Delete Subscriptions

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('bb885255-ccac-47e1-a491-2630f205df58')
    def test_delete_subscription_from_a_non_existing_queue(self):
        # Delete subscription from a non existing queue
        rbody = {'subscriber': 'http://fake123:8080',
                 'options': {'MessagingKey': 'MessagingValue'},
                 'ttl': 2935}
        results = self.create_subscription(self.queue_name, rbody)
        subscription_id = results[1]["subscription_id"]
        non_existent_queue = data_utils.rand_name('rand_queuename')
        resp, _ = self.client.delete_subscription(non_existent_queue,
                                                  subscription_id)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('a7007b4b-1ab1-4121-9d59-afe5eb82d31c')
    def test_delete_subscription_using_a_nonexisting_id(self):
        # Delete subscription with non existent id
        results = self._create_subscriptions()
        subscription_id = uuidutils.generate_uuid()
        resp, _ = self.client.delete_subscription(self.queue_name,
                                                  subscription_id)
        self.assertEqual('204', resp['status'])
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('8faf37ee-4abe-4586-9e4b-ed896129a3e8')
    def test_delete_subscription_with_invalid_token(self):
        # X-Auth-Token is not provided
        results = self._create_subscriptions()
        subscription_id = results[0][1]["subscription_id"]
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.delete_subscription, self.queue_name,
                          subscription_id)
        for result in results:
            subscription_id = result[1]["subscription_id"]
            self.delete_subscription(self.queue_name, subscription_id)

    @classmethod
    def resource_cleanup(cls):
        cls.delete_queue(cls.queue_name)
        super(TestSubscriptionsNegative, cls).resource_cleanup()

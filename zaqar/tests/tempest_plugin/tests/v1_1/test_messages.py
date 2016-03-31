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

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from zaqar.tests.tempest_plugin.tests import base

CONF = config.CONF


class TestMessages(base.BaseV11MessagingTest):

    @classmethod
    def resource_setup(cls):
        super(TestMessages, cls).resource_setup()
        cls.queue_name = data_utils.rand_name('Queues-Test')
        # Create Queue
        cls.client.create_queue(cls.queue_name)

    def _post_messages(self, repeat=CONF.messaging.max_messages_per_page):
        message_body = self.generate_message_body(repeat=repeat)
        resp, body = self.post_messages(queue_name=self.queue_name,
                                        rbody=message_body)
        return resp, body

    @decorators.idempotent_id('7e506151-6870-404b-b746-801a72599418')
    def test_post_messages(self):
        # Post Messages
        resp, _ = self._post_messages()

        # Get on the posted messages
        message_uri = resp['location'][resp['location'].find('/v1.1'):]
        resp, _ = self.client.show_multiple_messages(message_uri)
        # The test has an assertion here, because the response cannot be 204
        # in this case (the client allows 200 or 204 for this API call).
        self.assertEqual('200', resp['status'])

    @decorators.idempotent_id('d50ae94e-5f84-4e2d-bda4-48d8ab3ee3af')
    def test_list_messages(self):
        # Post Messages
        self._post_messages()

        # List Messages
        resp, _ = self.list_messages(queue_name=self.queue_name)
        # The test has an assertion here, because the response cannot be 204
        # in this case (the client allows 200 or 204 for this API call).
        self.assertEqual('200', resp['status'])

    @decorators.idempotent_id('a679d6be-f2ef-4649-b03c-710c72126b2f')
    def test_get_message(self):
        # Post Messages
        _, body = self._post_messages()
        message_uri = body['resources'][0]

        # Get posted message
        resp, _ = self.client.show_single_message(message_uri)
        # The test has an assertion here, because the response cannot be 204
        # in this case (the client allows 200 or 204 for this API call).
        self.assertEqual('200', resp['status'])

    @decorators.idempotent_id('889e7263-2d0c-4de1-aebd-d192157e347d')
    def test_get_multiple_messages(self):
        # Post Messages
        resp, _ = self._post_messages()
        message_uri = resp['location'][resp['location'].find('/v1.1'):]

        # Get posted messages
        resp, _ = self.client.show_multiple_messages(message_uri)
        # The test has an assertion here, because the response cannot be 204
        # in this case (the client allows 200 or 204 for this API call).
        self.assertEqual('200', resp['status'])

    @decorators.idempotent_id('9a932955-933e-4283-86d0-85dd121c2edf')
    def test_delete_single_message(self):
        # Post Messages
        _, body = self._post_messages()
        message_uri = body['resources'][0]

        # Delete posted message & verify the delete operration
        self.client.delete_messages(message_uri)

        message_uri = message_uri.replace('/messages/', '/messages?ids=')
        # The test has an assertion here, because the response has to be 404
        # in this case(different from v1).
        self.assertRaises(lib_exc.NotFound,
                          self.client.show_multiple_messages,
                          message_uri)

    @decorators.idempotent_id('ad1949a7-36c0-45be-8020-df91467d0bbb')
    def test_delete_multiple_messages(self):
        # Post Messages
        resp, _ = self._post_messages()
        message_uri = resp['location'][resp['location'].find('/v1.1'):]

        # Delete multiple messages
        self.client.delete_messages(message_uri)
        # The test has an assertion here, because the response has to be 404
        # in this case(different from v1).
        self.assertRaises(lib_exc.NotFound,
                          self.client.show_multiple_messages,
                          message_uri)

    @classmethod
    def resource_cleanup(cls):
        cls.delete_queue(cls.queue_name)
        super(TestMessages, cls).resource_cleanup()

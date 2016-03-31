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


class TestMessages(base.BaseV2MessagingTest):

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

    @decorators.idempotent_id('2e1a26c1-6d7b-4ae7-b510-d8e2abe9d831')
    def test_post_messages(self):
        # Post Messages
        resp, _ = self._post_messages()

        # Get on the posted messages
        message_uri = resp['location'][resp['location'].find('/v2'):]
        resp, _ = self.client.show_multiple_messages(message_uri)
        # The test has an assertion here, because the response cannot be 204
        # in this case (the client allows 200 or 204 for this API call).
        self.assertEqual('200', resp['status'])

    @decorators.idempotent_id('f38cca63-55d7-41e7-8ff9-7254e9859aa7')
    def test_list_messages(self):
        # Post Messages
        self._post_messages()

        # List Messages
        resp, _ = self.list_messages(queue_name=self.queue_name)
        # The test has an assertion here, because the response cannot be 204
        # in this case (the client allows 200 or 204 for this API call).
        self.assertEqual('200', resp['status'])

    @decorators.idempotent_id('f9719398-8bb7-4660-acb6-ef87c47d726c')
    def test_get_message(self):
        # Post Messages
        _, body = self._post_messages()
        message_uri = body['resources'][0]

        # Get posted message
        resp, _ = self.client.show_single_message(message_uri)
        # The test has an assertion here, because the response cannot be 204
        # in this case (the client allows 200 or 204 for this API call).
        self.assertEqual('200', resp['status'])

    @decorators.idempotent_id('a8fe2c0f-c3f2-4278-8bd9-2fca94356f2e')
    def test_get_multiple_messages(self):
        # Post Messages
        resp, _ = self._post_messages()
        message_uri = resp['location'][resp['location'].find('/v2'):]

        # Get posted messages
        resp, _ = self.client.show_multiple_messages(message_uri)
        # The test has an assertion here, because the response cannot be 204
        # in this case (the client allows 200 or 204 for this API call).
        self.assertEqual('200', resp['status'])

    @decorators.idempotent_id('9654fb55-8cbd-4997-8c3e-8d388276a8d9')
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

    @decorators.idempotent_id('e025555a-fa3f-4558-859a-42d69ccf66a6')
    def test_delete_multiple_messages(self):
        # Post Messages
        resp, _ = self._post_messages()
        message_uri = resp['location'][resp['location'].find('/v2'):]

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

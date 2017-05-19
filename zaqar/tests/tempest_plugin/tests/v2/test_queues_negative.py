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

from six import moves
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from zaqar.tests.tempest_plugin.tests import base


class QueueNegativeTestJSON(base.BaseV2MessagingTest):

    @classmethod
    def resource_setup(cls):
        super(QueueNegativeTestJSON, cls).resource_setup()
        cls.queues = list()
        for _ in moves.xrange(1):
            queue_name = data_utils.rand_name('Queues-Test')
            cls.queues.append(queue_name)
            cls.client.create_queue(queue_name)

    # Create Queues

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('77634fd0-0a25-4cc7-a01c-b6d16304f907')
    def test_queue_has_a_long_name(self):
        # Length of queue name should >= 1 and <=64 bytes
        queue_name = 'q' * 65
        self.assertRaises(lib_exc.BadRequest,
                          self.client.create_queue,
                          queue_name)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('639206ad-d74c-4f51-895d-76e2c7dff60b')
    def test_queue_name_is_not_specified(self):
        # Length of queue name should >= 1 and <=64 bytes
        queue_name = ' '
        self.assertRaises(lib_exc.UnexpectedResponseCode,
                          self.client.create_queue,
                          queue_name)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('3ca0e180-c770-4922-8a48-9563c484aaed')
    def test_queue_name_has_a_invalid_character_set(self):
        # Invalid name with characters
        queue_name = '@$@^qw@'
        self.assertRaises(lib_exc.BadRequest,
                          self.client.create_queue,
                          queue_name)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('533c5a65-fcc9-4e07-84bc-82ac0c007dbc')
    def test_queue_name_with_non_ASCII_characters(self):
        # Invalid name with non-ASCII characters
        queue_name = data_utils.rand_name('\u6c49\u5b57\u6f22\u5b57')
        self.assertRaises(lib_exc.BadRequest,
                          self.client.create_queue,
                          queue_name)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('44775212-2b79-40c7-8604-fcf01eddba79')
    def test_queue_name_with_numeric_values(self):
        # Numeric values for  queue name
        queue_name = data_utils.rand_int_id()
        resp, _ = self.client.create_queue(queue_name)
        self.assertEqual('201', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('2ce4f4c1-cbaa-4c2d-b28a-f562aec037aa')
    def test_create_queue_with_invalid_auth_token(self):
        # Create queue with empty headers
        # X-Auth-Token is not provided
        queue_name = data_utils.rand_name(name='queue')
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.create_queue,
                          queue_name)

    # List Queues

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('d4d33596-0f06-4911-aecc-17512c00a301')
    def test_request_a_nonexistent_queue(self):
        # List a non-existent queue
        nonexistent_queuename = data_utils.rand_name('rand_queuename')
        resp, _ = self.client.show_queue(nonexistent_queuename)
        self.assertEqual('200', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('0c8122a8-e28b-4320-8f1f-af97a0bfa26b')
    def test_request_after_deleting_queue(self):
        # Request queue after deleting the queue
        # DELETE is an idempotent operation
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        self.client.delete_queue(queue_name)
        resp, _ = self.client.show_queue(queue_name)
        self.assertEqual('200', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('b7c4521a-d0f1-4fc6-b99d-ece2131ac082')
    def test_request_with_a_greater_limit_value(self):
        # Limit for listing queues is 20 , configurable
        params = {'limit': '200'}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.list_queues,
                          url_params=params)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('121e5171-e189-4be5-8ccf-d0b2009b3bbe')
    def test_request_with_zero_limit_value(self):
        # Limit for listing queues is 20 , configurable
        params = {'limit': '0'}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.list_queues,
                          url_params=params)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('6c710fa6-9447-4c2c-b8c0-7581a56b4ab5')
    def test_request_with_negative_limit_value(self):
        # Limit for listing queues is 20 , configurable
        params = {'limit': '-1'}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.list_queues,
                          url_params=params)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('4a54b60c-0a6a-4662-9ba1-fe0b9dd4f399')
    def test_with_non_boolean_value_for_detailed(self):
        # Value for detailed parameter should be true or false
        params = {'detailed': 'None'}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.list_queues, url_params=params)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('f66f1225-bfe8-4fe0-b8c9-35e4342e0f0e')
    def test_list_queues_with_invalid_auth_token(self):
        # List queue with empty headers
        # X-Auth-Token is not provided
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.list_queues)

    # Get Queue Stats

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('16cec0df-b58a-44e8-9132-f99f0c1da29a')
    def test_request_stats_for_a_non_existing_queue(self):
        # Show stats for a non-existent queue
        nonexistent_queuename = data_utils.rand_name('rand_queuename')
        resp, _ = self.client.show_queue_stats(nonexistent_queuename)
        self.assertEqual('200', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('1cad4984-3f66-48f6-82c9-9a544be78ca6')
    def test_request_queue_stats_after_deleting_queue(self):
        # List queue stats after deleting the queue
        # DELETE is an idempotent operation
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        self.client.delete_queue(queue_name)
        resp, _ = self.client.show_queue_stats(queue_name)
        self.assertEqual('200', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('2b1aeba8-a314-495b-8d45-84692354a013')
    def test_request_queue_stats_with_invalid_auth_token(self):
        # Get queue stats with empty headers
        # X-Auth-Token is not provided
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.show_queue_stats,
                          queue_name)

    # Delete Queues

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('cf7d5cff-0e4f-4d2c-82eb-59f450ca1b7d')
    def test_delete_a_non_existing_queue(self):
        # Delete is an idempotent operation
        non_existent_queue = data_utils.rand_name('Queue_name')
        resp, _ = self.client.delete_queue(non_existent_queue)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('c5973d87-5b59-446c-8e81-a8e28de9e61d')
    def test_delete_the_deleted_queue(self):
        # Delete is an idempotent operation
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        self.client.delete_queue(queue_name)
        # Delete again
        resp, _ = self.client.delete_queue(queue_name)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('a54e2715-478a-4701-9080-a06b9364dc74')
    def test_delete_queue_with_invalid_auth_token(self):
        # Delete queue with empty headers
        # X-Auth-Token is not provided
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.delete_queue,
                          queue_name)

    @classmethod
    def resource_cleanup(cls):
        for queue_name in cls.queues:
            cls.client.delete_queue(queue_name)
        super(QueueNegativeTestJSON, cls).resource_cleanup()

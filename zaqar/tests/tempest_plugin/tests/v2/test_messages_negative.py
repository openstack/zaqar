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

import random

from oslo_utils import uuidutils
from six import moves
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from zaqar.tests.tempest_plugin.tests import base

CONF = config.CONF


class TestMessagesNegative(base.BaseV2MessagingTest):

    @classmethod
    def resource_setup(cls):
        super(TestMessagesNegative, cls).resource_setup()
        cls.queues = list()
        for _ in moves.xrange(1):
            queue_name = data_utils.rand_name('Queues-Test')
            cls.queues.append(queue_name)
            # Create Queue
            cls.client.create_queue(queue_name)

    # Get specific Message

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('8246ee51-651c-4e2a-9a07-91848ca5e1e4')
    def test_request_single_message_from_a_nonexistent_queue(self):
        # List a message from a nonexistent queue
        id = uuidutils.generate_uuid()
        non_existent_queue = data_utils.rand_name('rand_queuename')
        uri = "/v2/queues/{0}/messages/{1}".format(non_existent_queue, id)
        self.assertRaises(lib_exc.NotFound,
                          self.client.show_single_message, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('767fdad1-37df-485a-8063-5036e8d16a12')
    def test_request_a_non_existing_message(self):
        # List a message with an invalid id
        invalid_id = uuidutils.generate_uuid()
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        uri = "/v2/queues/{0}/messages/{1}".format(queue_name, invalid_id)
        self.assertRaises(lib_exc.NotFound,
                          self.client.show_single_message, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ac2d1a88-5721-4bef-8dfa-53d936630e84')
    def test_request_a_message_with_negative_message_id(self):
        # List a message with an invalid id, negative
        negative_id = '-1'
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        uri = "/v2/queues/{0}/messages?ids={1}".format(queue_name,
                                                       negative_id)
        self.assertRaises(lib_exc.NotFound,
                          self.client.show_single_message, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ac083d78-67bb-4515-b553-2fc76499e2bd')
    def test_request_a_message_without_a_token(self):
        # List a message without a valid token
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        id = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/messages/{1}".format(queue_name, id)
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.show_single_message, uri)

    # Get a Set of Messages by ID

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('f544e745-f3da-451d-8621-c3711cd37453')
    def test_request_multiple_messages_from_a_nonexistent_queue(self):
        # List multiple messages from a non existent queue
        id1 = uuidutils.generate_uuid()
        id2 = uuidutils.generate_uuid()
        queue = data_utils.rand_name('nonexistent_queue')
        uri = "/v2/queues/{0}/messages?ids={1},{2}".format(queue,
                                                           id1, id2)
        self.assertRaises(lib_exc.NotFound,
                          self.client.show_multiple_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('654e64f8-01df-40a0-a09e-d5ec17a3e187')
    def test_request_multiple_messages_with_invalid_message_id(self):
        # List multiple messages by passing invalid id
        invalid_id = uuidutils.generate_uuid()
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        uri = "/v2/queues/{0}/messages?ids={1},{2}".format(queue_name,
                                                           invalid_id,
                                                           invalid_id)
        self.assertRaises(lib_exc.NotFound,
                          self.client.show_multiple_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('295a37a6-5c93-43e3-a316-3f3dffd4b242')
    def test_request_multiple_messages_by_exceeding_the_default_limit(self):
        # Default limit value is 20 , configurable
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        ids = str.join(',', (uuidutils.generate_uuid()) * 21)
        uri = "/v2/queues/{0}/messages?ids={1}".format(queue_name, ids)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.show_multiple_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('f96eb4a0-8930-4d5e-b8bf-11080628c761')
    def test_request_message_by_passing_invalid_echo_param(self):
        # Value of the echo parameter must be either true or false
        echo = None
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        uri = "/v2/queues/{0}/messages?echo={1}".format(queue_name, echo)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.show_multiple_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('6f668242-6a45-48bc-8ef2-fb581e57d471')
    def test_request_messages_by_passing_invalid_include_claimed_param(self):
        # Value of include_claimed param must be either true or false
        value = None
        queue = self.queues[data_utils.rand_int_id(0,
                                                   len(self.queues) - 1)]
        uri = "/v2/queues/{0}/messages?include_claimed={1}".format(queue,
                                                                   value)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.show_multiple_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('dd267387-76f6-47bd-849b-b1640051aff4')
    def test_request_messages_limit_greater_than_configured_value(self):
        # Default limit value is 20 , configurable
        invalid_limit = data_utils.rand_int_id(21, 10000)
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        uri = "/v2/queues/{0}/messages?limit={1}".format(queue_name,
                                                         invalid_limit)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.show_multiple_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('d199f64e-0f22-4129-9bc4-ff709c01592b')
    def test_request_messages_with_limit_less_than_configured_value(self):
        # Default limit value is 20 , configurable
        invalid_limit = data_utils.rand_int_id(-1000, 0)
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        uri = "/v2/queues/{0}/messages?limit={1}".format(queue_name,
                                                         invalid_limit)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.show_multiple_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('0b2e803c-7cb9-4c11-bed6-f976f5247b27')
    def test_request_multiple_messages_request_without_a_token(self):
        # List messages without a valid token
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        id1 = uuidutils.generate_uuid()
        id2 = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/messages/{1},{2}".format(queue_name, id1, id2)
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.show_multiple_messages, uri)

    # Get Messages

    @decorators.idempotent_id('125632c4-c7ce-47fb-93fe-c446d14396f9')
    def test_list_messages_with_invalid_token(self):
        # List messages without a valid token
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.list_messages, queue_name)

    # Post Messages

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('5a0ba3e6-e6ca-4952-be50-fb6be7834ab7')
    def test_post_messages_with_no_request_body(self):
        # Post message with empty body
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        body = {}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('af5ffb4d-c0b4-41db-aea3-bcfc8a232bd6')
    def test_post_messages_with_a_bad_message(self):
        # Post message with invalid message format
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        body = {'[]', '.'}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('10bc153c-97d2-4a19-9795-e0f6993bad4f')
    def test_post_messages_to_a_nonexistent_queue(self):
        # Post message to a non existent queue
        non_existent_queue = data_utils.rand_name('rand_queuename')
        body = self.generate_message_body()
        resp, _ = self.client.post_messages(non_existent_queue, body)
        self.assertEqual('201', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('263d6361-4759-4f2c-be9c-12559f064135')
    def test_post_messages_to_a_non_ascii_queue(self):
        # Post message to a queue with non ascii queue name
        queue_name = data_utils.rand_name('\u6c49\u5b57\u6f22\u5b57')
        body = self.generate_message_body()
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('04c1b220-1e22-4e38-9db2-a76e8b5e2f3f')
    def test_post_messages_to_a_queue_with_invalid_name(self):
        # Post messages to a queue with invalid characters for queue name
        queue_name = '@$@^qw@'
        body = self.generate_message_body()
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('72290766-cb01-425e-856b-a57877015336')
    def test_post_messages_to_a_queue_with_invalid_length_for_queue_name(self):
        # Post messages to a queue with a long queue name
        queue_name = 'q' * 65
        body = self.generate_message_body()
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('774e8bc8-9b20-40fb-9eed-c5368de368c5')
    def test_post_messages_with_invalid_json_request_body(self):
        # Post messages to a queue with non-JSON request body
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        body = "123"
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ebbe257a-9f1e-498a-bba8-f5c71230365a')
    def test_post_messages_with_TTL_less_than_60(self):
        # TTL for a message may not exceed 1209600 seconds,
        # and must be at least 60 seconds long.
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_ttl = data_utils.\
            rand_int_id(start=0, end=60)

        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        message_body = {key: value}

        rbody = ([{'body': message_body, 'ttl': message_ttl}] * 1)

        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('6d64de03-fd57-4f07-b6f1-8563200a4b4d')
    def test_post_messages_with_TTL_greater_than_1209600(self):
        # TTL for a message may not exceed 1209600 seconds, and
        # must be at least 60 seconds long.
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_ttl = data_utils.\
            rand_int_id(start=1209601, end=1309600)

        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        message_body = {key: value}

        rbody = ([{'body': message_body, 'ttl': message_ttl}] * 1)

        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('c48802d7-7e91-4d5f-9c23-32cd4edc41ff')
    def test_post_messages_with_non_int_value_of_TTL(self):
        # TTL for a message may not exceed 1209600 seconds, and
        # must be at least 60 seconds long.
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_ttl = random.uniform(0.0, 0.120960)

        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        message_body = {key: value}

        rbody = ([{'body': message_body, 'ttl': message_ttl}] * 1)

        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('203fed96-0df3-43c0-9956-723b34b8a23b')
    def test_post_messages_with_negative_value_of_TTL(self):
        # TTL for a message may not exceed 1209600 seconds, and
        # must be at least 60 seconds long.
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_ttl = data_utils.\
            rand_int_id(start=-9999, end=-1)

        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        message_body = {key: value}

        rbody = ([{'body': message_body, 'ttl': message_ttl}] * 1)

        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('d3ad28e7-0c84-43cf-bb87-1574da28a10d')
    def test_post_messages_without_TTL(self):
        # TTL for a message may not exceed 1209600 seconds, and
        # must be at least 60 seconds long.
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        message_body = {key: value}

        rbody = ([{'body': message_body}] * 1)

        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('662428d4-302f-4000-8ac6-1a53fb8818b8')
    def test_post_messages_exceeding_message_post_size(self):
        # Post messages with greater message size
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = 'a' * 1024
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)

        message_body = {key: value}

        rbody = ([{'body': message_body, 'ttl': message_ttl}] * 1)

        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ba4f7334-1a4d-4bc8-acd3-040a1310fe62')
    def test_post_messages_with_invalid_body_size(self):
        # Maximum number of queue message per page
        # while posting messages is 20
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)

        message_body = {key: value}
        rbody = ([{'body': message_body, 'ttl': message_ttl}] * 21)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('855d36a2-e583-4355-af33-fcec0f71842c')
    def test_post_messages_without_body_in_request_body(self):
        # TTL for a message may not exceed 1209600 seconds, and
        # must be at least 60 seconds long.
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)

        rbody = ([{'ttl': message_ttl}] * 1)

        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_messages, queue_name, rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('074fe312-0077-41ba-8aa9-e6d6a586a685')
    def test_post_messages_with_invalid_auth_token(self):
        # X-Auth-Token is not provided
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        body = self.generate_message_body()
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None)
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.post_messages,
                          queue_name, body)

    # Delete Messages

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('8552d5b3-7c16-4eaf-a8de-a7b178823458')
    def test_delete_message_from_a_nonexistent_queue(self):
        # Delete is an idempotent operation
        non_existent_queue = data_utils.rand_name('rand_queuename')
        message_id = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/messages?ids={1}".format(non_existent_queue,
                                                       message_id)
        resp, _ = self.client.delete_messages(uri)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('a5d581f0-0403-4c2d-9ea4-048cc6cc85f0')
    def test_delete_a_non_existing_message(self):
        # Delete is an idempotent operation
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_id = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/messages?ids={1}".format(queue_name,
                                                       message_id)
        resp, _ = self.client.delete_messages(uri)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('f792f462-0ad9-41b1-9bae-636957364ca0')
    def test_delete_message_with_non_existent_message_id(self):
        # Delete is an idempotent operation
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_id = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/messages/{1}".format(queue_name,
                                                   message_id)
        resp, _ = self.client.delete_messages(uri)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('6b8f14b3-2307-49e2-aa53-75d4d4b82754')
    def test_delete_multiple_non_existing_messages(self):
        # Delete is an idempotent operation
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        id1 = uuidutils.generate_uuid()
        id2 = uuidutils.generate_uuid()
        id3 = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/messages?ids={1}{2}{3}".format(queue_name,
                                                             id1, id2, id3)
        resp, _ = self.client.delete_messages(uri)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('805f75fd-6447-4c8a-860c-2659d8a5b0b5')
    def test_delete_message_without_id(self):
        # Delete all the message from a queue
        # without passing any id
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_body = self.generate_message_body(repeat=1)
        self.post_messages(queue_name, message_body)
        uri = "/v2/queues/{0}/messages".format(queue_name)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.delete_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('85eed2fb-fa72-4886-8cfc-44c7fb58ffea')
    def test_delete_message_with_invalid_message_id(self):
        # Delete is an idempotent operation
        # Delete a message with negative id
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_id = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/messages?ids=-{1}".format(queue_name,
                                                        message_id)
        resp, _ = self.client.delete_messages(uri)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('374265e7-1146-4da4-a265-38c8698e4144')
    def test_delete_the_deleted_message(self):
        # Delete is an idempotent operation
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_id = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/messages?ids={1}".format(queue_name,
                                                       message_id)
        resp, _ = self.client.delete_messages(uri)
        # Delete the message again
        resp, _ = self.client.delete_messages(uri)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('a130d499-cd41-42dd-b1f0-e859f73b00e0')
    def test_delete_multiple_messages_by_exceeding_the_default_limit(self):
        # Default limit value is 20
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        ids = str.join(',', (uuidutils.generate_uuid()) * 21)
        uri = "/v2/queues/{0}/messages?ids={1}".format(queue_name, ids)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.delete_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('51a2f5ca-e358-4ef6-9f33-73d3e01f07b9')
    def test_delete_message_without_providing_claim_id(self):
        # When message is claimed;
        # it cannot be deleted without a valid claim ID.
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        # Post Messages
        message_body = self.generate_message_body(repeat=1)
        self.client.post_messages(queue_name=queue_name,
                                  rbody=message_body)
        # Post Claim
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        resp, body = self.client.post_claims(queue_name=queue_name,
                                             rbody=claim_body)
        message_uri = body['messages'][0]['href']
        sep = "?claim_id"
        uri = message_uri.split(sep, 1)[0]
        self.assertRaises(lib_exc.Forbidden,
                          self.client.delete_messages,
                          uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('18fa5f43-20e6-47bd-a751-ef33e62a4315')
    def test_delete_message_with_invalid_claim_id(self):
        # Delete with a non existent claim id
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_body = self.generate_message_body(repeat=1)
        resp, body = self.post_messages(queue_name, message_body)
        message_uri = body['resources'][0]
        claim_id = "?claim_id=123"
        uri = message_uri + str(claim_id)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.delete_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('b82e5dee-5470-4408-9dca-d4a7536ff25f')
    def test_delete_message_with_no_pop_value(self):
        # Pop value must be at least 1 and may not be greater than 20
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        value = ' '
        uri = "/v2/queues/{0}/messages?pop={1}".format(queue_name, value)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.delete_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('6454103d-9cfd-48da-bd8c-061e61a7e634')
    def test_delete_message_with_invalid_pop_value(self):
        # Pop value must be at least 1 and may not be greater than 20
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        value = 1000000000
        uri = "/v2/queues/{0}/messages?pop={1}".format(queue_name, value)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.delete_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('9874b696-352b-47d7-a338-d149d4096c28')
    def test_delete_message_with_negative_pop_value(self):
        # Pop value must be at least 1 and may not be greater than 20
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        value = '-1'
        uri = "/v2/queues/{0}/messages?pop={1}".format(queue_name, value)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.delete_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('4044f38a-0a70-4c86-ab1b-ca369e5b443a')
    def test_delete_message_with_invalid_params_with_pop(self):
        # Pop & ids parameters are mutually exclusive
        # Anyone of which needs to be used with delete
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        pop_value = 5
        ids_value = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/messages?pop={1}&ids={2}".format(queue_name,
                                                               pop_value,
                                                               ids_value)
        self.assertRaises(lib_exc.BadRequest,
                          self.client.delete_messages, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('ea609ee5-a7a2-41a0-a9fb-73e8c7ed8c59')
    def test_delete_messages_with_invalid_auth_token(self):
        # Delete message with an invalid token
        queue_name = self.queues[data_utils.rand_int_id(0,
                                                        len(self.queues) - 1)]
        message_body = self.generate_message_body(repeat=1)
        resp, body = self.post_messages(queue_name, message_body)
        message_uri = body['resources'][0]
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None)
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.delete_messages,
                          message_uri)

    @classmethod
    def resource_cleanup(cls):
        for queue_name in cls.queues:
            cls.client.delete_queue(queue_name)
        super(TestMessagesNegative, cls).resource_cleanup()

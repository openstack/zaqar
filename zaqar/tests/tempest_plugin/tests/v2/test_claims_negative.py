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


class TestClaimsNegative(base.BaseV2MessagingTest):

    @classmethod
    def resource_setup(cls):
        super(TestClaimsNegative, cls).resource_setup()
        cls.queue_name = data_utils.rand_name('Queues-Test')
        # Create Queue
        cls.create_queue(cls.queue_name)

    def _post_and_claim_messages(self, queue_name, repeat=1):
        # Post Messages
        message_body = self.generate_message_body(repeat=repeat)
        self.client.post_messages(queue_name=self.queue_name,
                                  rbody=message_body)

        # Post Claim
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        resp, body = self.client.post_claims(queue_name=self.queue_name,
                                             rbody=claim_body)
        return resp, body

    # Claim Messages

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('bd524990-7dff-4950-a82b-554ef1d644b6')
    def test_request_claim_message_with_no_request_body(self):
        # Claim a message with no request body
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)

        claim_body = {}
        resp, _ = self.client.post_claims(self.queue_name,
                                          claim_body)
        self.assertEqual('201', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('21de9b01-00a7-406a-a2e7-86ecfea2f21a')
    def test_request_claim_message_with_invalid_character_request_body(self):
        # Claim a message with invalid characters as request body
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)

        claim_body = '['
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_claims, self.queue_name,
                          claim_body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('5149cf66-0273-438c-b9de-f8c4af56f382')
    def test_request_claim_message_with_invalid_request_body(self):
        # Claim a message with invalid request body
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)

        claim_body = '"Try"'
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_claims, self.queue_name,
                          claim_body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('9537b022-659e-4220-a05d-eabc10661772')
    def test_request_claim_message_with_greater_value_for_limit(self):
        # Claim messages with a greater limit value
        message_body = self.generate_message_body(repeat=1)
        self.client.post_messages(queue_name=self.queue_name,
                                  rbody=message_body)
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        params = {'limit': 200}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_claims, self.queue_name,
                          claim_body, url_params=params)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('b9160f04-31f0-4246-b879-329b806a0d8a')
    def test_request_claim_message_with_lesser_value_for_limit(self):
        # Claim messages with an invalid lesser value
        message_body = self.generate_message_body(repeat=1)
        _, body = self.client.post_messages(queue_name=self.queue_name,
                                            rbody=message_body)
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        params = {'limit': 0}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_claims, self.queue_name,
                          claim_body, url_params=params)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('5dfa2fa4-ca17-46f3-9a28-8e70fbbd7f9e')
    def test_request_claim_message_with_negative_value_for_limit(self):
        # Claim messages with a negative value of limit
        message_body = self.generate_message_body(repeat=1)
        _, body = self.client.post_messages(queue_name=self.queue_name,
                                            rbody=message_body)
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}

        params = {'limit': -1}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_claims, self.queue_name,
                          claim_body, url_params=params)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('eb8025bb-0f42-42fd-9905-6376bdc74cf4')
    def test_request_claim_message_with_no_TTL_field(self):
        # Claim a message with no TTL field
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)

        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"grace": claim_grace}
        resp, _ = self.client.post_claims(self.queue_name,
                                          claim_body)
        self.assertEqual('201', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('6b99cab8-17f0-4ec5-bb6a-9ad490a0eb7a')
    def test_request_claim_message_with_greater_invalid_TTL_value(self):
        # TTL for a claim may not exceed 1209600 seconds,
        # and must be at least 60 seconds long , configurable
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)
        claim_ttl = data_utils.rand_int_id(start=43201,
                                           end=43500)
        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_claims, self.queue_name, claim_body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('3d65af6e-b104-40a6-a15c-1cf65358e687')
    def test_request_claim_message_with_lesser_invalid_TTL_value(self):
        # TTL for a claim may not exceed 1209600 seconds,
        # and must be at least 60 seconds long , configurable
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)
        claim_ttl = data_utils.rand_int_id(start=-43500,
                                           end=0)
        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_claims, self.queue_name, claim_body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('86978d35-65be-44bb-aba4-0610728b5399')
    def test_request_claim_message_with_no_grace_field(self):
        # Grace for a claim may not exceed 1209600 seconds,
        # and must be at least 60 seconds long , configurable
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_body = {"ttl": claim_ttl}
        resp, _ = self.client.post_claims(self.queue_name,
                                          claim_body)
        self.assertEqual('201', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('812d9092-2d59-4dae-b67d-ce00da3f74f9')
    def test_request_claim_message_with_invalid_greater_grace_value(self):
        # Grace for a claim may not exceed 1209600 seconds,
        # and must be at least 60 seconds long , configurable
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_grace = data_utils.\
            rand_int_id(start=43201, end=43501)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_claims, self.queue_name, claim_body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('bf10b08c-e254-49e4-a751-a0e128dce618')
    def test_request_claim_message_with_invalid_lesser_grace_value(self):
        # Grace for a claim may not exceed 1209600 seconds,
        # and must be at least 60 seconds long , configurable
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_grace = data_utils.\
            rand_int_id(start=-43201, end=0)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_claims, self.queue_name, claim_body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('69b0d11a-40f5-4f35-847f-05f92ffadeb3')
    def test_request_claim_message_with_non_JSON_request_body(self):
        # Claim a messsage with an invalid JSON
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)
        claim_body = "123"
        self.assertRaises(lib_exc.BadRequest,
                          self.client.post_claims, self.queue_name, claim_body)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('d145ea04-203d-41f9-a893-f6e5716005b6')
    def test_request_claim_message_with_invalid_url_params(self):
        # Post Messages
        message_body = self.generate_message_body(repeat=1)
        _, body = self.client.post_messages(queue_name=self.queue_name,
                                            rbody=message_body)
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        params = {'Invalid': 'ImAnInvalidParam'}
        resp, _ = self.client.post_claims(self.queue_name,
                                          claim_body, url_params=params)
        self.assertEqual('201', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('dbdf17ce-879f-4688-b71c-260cb9e4c4ab')
    def test_claim_message_with_invalid_token(self):
        # Claim a message without a valid token
        body = self.generate_message_body()
        self.client.post_messages(self.queue_name, body)

        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        claim_grace = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_claim_grace)
        claim_body = {"ttl": claim_ttl, "grace": claim_grace}
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.post_claims, self.queue_name, claim_body)

    # Query Claim

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('a1844a12-62d6-435e-906b-6b6ae538834f')
    def test_query_from_a_nonexistent_queue(self):
        # Query claim a non existent queue
        non_existent_queue = data_utils.rand_name('rand_queuename')
        non_existent_id = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/claims/{1}".format(non_existent_queue,
                                                 non_existent_id)
        self.assertRaises(lib_exc.NotFound,
                          self.client.query_claim, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('a2af8e9b-08fb-4079-a77a-28c0390a614a')
    def test_query_claim_with_non_existing_claim_id(self):
        # Query claim using a non existing claim id
        non_existent_id = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/claims/{1}".format(self.queue_name,
                                                 non_existent_id)
        self.assertRaises(lib_exc.NotFound,
                          self.client.query_claim, uri)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('a58c5214-68b9-47d6-a036-de73e7b2cdad')
    def test_query_claim_with_invalid_token(self):
        # Query claim with an invalid token
        resp, body = self._post_and_claim_messages(queue_name=self.queue_name)
        claim_uri = resp['location'][resp['location'].find('/v2'):]
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.query_claim, claim_uri)

    # Update Claim

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('28915079-8b20-487d-ab01-64218572c543')
    def test_update_claim_on_non_existing_queue(self):
        # Update claim on a non existing queue
        resp, body = self._post_and_claim_messages(queue_name=self.queue_name)
        self.client.delete_queue(self.queue_name)
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        update_rbody = {"ttl": claim_ttl}
        claim_uri = resp['location'][resp['location'].find('/v2'):]
        self.assertRaises(lib_exc.NotFound,
                          self.client.update_claim, claim_uri, update_rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('732e9ca6-6e4f-4d66-9e78-200c3d6aca88')
    def test_update_a_non_existing_claim(self):
        # Update a non existing claim
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        update_rbody = {"ttl": claim_ttl}
        claim_id = uuidutils.generate_uuid()
        claim_uri = "/v2/queues/{0}/claims/{1}".format(self.queue_name,
                                                       claim_id)
        self.assertRaises(lib_exc.NotFound,
                          self.client.update_claim, claim_uri, update_rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('925514e9-57f0-4209-a64e-8b0a72bb8f0f')
    def test_update_claim_with_no_request_body(self):
        # Update claim with no request body
        resp, body = self._post_and_claim_messages(self.queue_name)
        update_rbody = {}
        claim_uri = resp['location'][resp['location'].find('/v2'):]
        resp, body = self.client.update_claim(claim_uri, update_rbody)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('c17793da-112a-4e90-b2fd-a5acbfdcddc5')
    def test_update_claim_with_invalid_json_in_request_body(self):
        # Update claim with an invalid JSON
        resp, body = self._post_and_claim_messages(self.queue_name)
        update_rbody = {"123"}
        claim_uri = resp['location'][resp['location'].find('/v2'):]
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_claim, claim_uri, update_rbody)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('1cd2fed7-6840-49cd-9b7a-1d80c01300fb')
    def test_update_claim_with_invalid_token(self):
        # Update claim without a valid token
        resp, body = self._post_and_claim_messages(self.queue_name)
        claim_uri = resp['location'][resp['location'].find('/v2'):]
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        update_rbody = {"ttl": claim_ttl}
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.update_claim, claim_uri, update_rbody)

    # Release Claim

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('b61a0d09-bc47-4b33-aa6d-7f20cbbe9bd2')
    def test_release_claim_from_a_non_existing_queue(self):
        # Release claim from a non existing queue
        non_existent_queue = data_utils.rand_name('rand_queuename')
        non_existent_id = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/claims/{1}".format(non_existent_queue,
                                                 non_existent_id)
        resp, body = self.client.delete_claim(uri)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('20a6e6ed-0f53-484d-aa78-717cdaa25e50')
    def test_release_a_nonexisting_claim_id(self):
        # Release a non existing claim
        non_existent_id = uuidutils.generate_uuid()
        uri = "/v2/queues/{0}/claims/{1}".format(self.queue_name,
                                                 non_existent_id)
        resp, body = self.client.delete_claim(uri)
        self.assertEqual('204', resp['status'])

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('082d50ca-bd3e-4d66-a92b-6ff917ab3b21')
    def test_release_claim_with_invalid_token(self):
        # Release claim without a valid token
        resp, body = self._post_and_claim_messages(queue_name=self.queue_name)
        claim_uri = resp['location'][resp['location'].find('/v2'):]
        self.client.auth_provider.set_alt_auth_data(
            request_part='headers',
            auth_data=None
        )
        self.assertRaises(lib_exc.Unauthorized,
                          self.client.delete_claim, claim_uri)

    @classmethod
    def resource_cleanup(cls):
        cls.delete_queue(cls.queue_name)
        super(TestClaimsNegative, cls).resource_cleanup()

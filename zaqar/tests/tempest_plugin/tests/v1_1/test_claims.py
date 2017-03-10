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

from six.moves.urllib import parse as urlparse
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators

from zaqar.tests.tempest_plugin.tests import base


CONF = config.CONF


class TestClaims(base.BaseV11MessagingTest):

    @classmethod
    def resource_setup(cls):
        super(TestClaims, cls).resource_setup()
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

    @decorators.idempotent_id('6fc4b79d-2366-4911-b0be-6446a1f02aea')
    def test_post_claim(self):
        _, body = self._post_and_claim_messages(queue_name=self.queue_name)
        claimed_message_uri = body['messages'][0]['href']

        # Delete Claimed message
        self.client.delete_messages(claimed_message_uri)

    @decorators.idempotent_id('c61829f9-104a-4860-a136-6af2a89f3eef')
    def test_query_claim(self):
        # Post a Claim
        resp, body = self._post_and_claim_messages(queue_name=self.queue_name)

        # Query Claim
        claim_uri = resp['location'][resp['location'].find('/v1.1'):]
        self.client.query_claim(claim_uri)

        # Delete Claimed message
        claimed_message_uri = body['messages'][0]['href']
        self.delete_messages(claimed_message_uri)

    @decorators.idempotent_id('57b9d065-1995-420f-9173-4d716339e3b9')
    def test_update_claim(self):
        # Post a Claim
        resp, body = self._post_and_claim_messages(queue_name=self.queue_name)

        claim_uri = resp['location'][resp['location'].find('/v1.1'):]
        claimed_message_uri = body['messages'][0]['href']

        # Update Claim
        claim_ttl = data_utils.rand_int_id(start=60,
                                           end=CONF.messaging.max_claim_ttl)
        update_rbody = {"ttl": claim_ttl}

        self.client.update_claim(claim_uri, rbody=update_rbody)

        # Verify claim ttl >= updated ttl value
        _, body = self.client.query_claim(claim_uri)
        updated_claim_ttl = body["ttl"]
        self.assertGreaterEqual(claim_ttl, updated_claim_ttl)

        # Delete Claimed message
        self.client.delete_messages(claimed_message_uri)

    @decorators.idempotent_id('71081c25-3eb4-427a-b2f3-891d0c5f7d32')
    def test_release_claim(self):
        # Post a Claim
        resp, body = self._post_and_claim_messages(queue_name=self.queue_name)
        claim_uri = resp['location'][resp['location'].find('/v1.1'):]

        # Release Claim
        self.client.delete_claim(claim_uri)

        # Delete Claimed message
        # This will implicitly verify that the claim is deleted.
        message_uri = urlparse.urlparse(claim_uri).path
        self.client.delete_messages(message_uri)

    @classmethod
    def resource_cleanup(cls):
        cls.delete_queue(cls.queue_name)
        super(TestClaims, cls).resource_cleanup()

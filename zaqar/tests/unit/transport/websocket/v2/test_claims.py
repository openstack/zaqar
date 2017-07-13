# Copyright (c) 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import json

import ddt
import mock
from oslo_utils import timeutils
from oslo_utils import uuidutils

from zaqar.common import consts
from zaqar.tests.unit.transport.websocket import base
from zaqar.tests.unit.transport.websocket import utils as test_utils


@ddt.ddt
class ClaimsBaseTest(base.V1_1Base):

    config_file = "websocket_mongodb.conf"

    def setUp(self):
        super(ClaimsBaseTest, self).setUp()
        self.protocol = self.transport.factory()
        self.defaults = self.api.get_defaults()

        self.project_id = '7e55e1a7e'
        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': self.project_id
        }

        action = consts.QUEUE_CREATE
        body = {"queue_name": "skittle"}
        req = test_utils.create_request(action, body, self.headers)

        with mock.patch.object(self.protocol, 'sendMessage') as msg_mock:
            self.protocol.onMessage(req, False)
            resp = json.loads(msg_mock.call_args[0][0])
            self.assertEqual(201, resp['headers']['status'])

        action = consts.MESSAGE_POST
        body = {"queue_name": "skittle",
                "messages": [
                    {'body': 239, 'ttl': 300},
                    {'body': {'key_1': 'value_1'}, 'ttl': 300},
                    {'body': [1, 3], 'ttl': 300},
                    {'body': 439, 'ttl': 300},
                    {'body': {'key_2': 'value_2'}, 'ttl': 300},
                    {'body': ['a', 'b'], 'ttl': 300},
                    {'body': 639, 'ttl': 300},
                    {'body': {'key_3': 'value_3'}, 'ttl': 300},
                    {'body': ["aa", "bb"], 'ttl': 300}]
                }

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(201, resp['headers']['status'])

    def tearDown(self):
        super(ClaimsBaseTest, self).tearDown()
        action = consts.QUEUE_DELETE
        body = {'queue_name': 'skittle'}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

    @ddt.data('[', '[]', '.', '"fail"')
    def test_bad_claim(self, doc):
        action = consts.CLAIM_CREATE
        body = doc

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

        action = consts.CLAIM_UPDATE
        body = doc

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    def test_exceeded_claim(self):
        action = consts.CLAIM_CREATE
        body = {"queue_name": "skittle",
                "ttl": 100,
                "grace": 60,
                "limit": 21}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    @ddt.data((-1, -1), (59, 60), (60, 59), (60, 43201), (43201, 60))
    def test_unacceptable_ttl_or_grace(self, ttl_grace):
        ttl, grace = ttl_grace
        action = consts.CLAIM_CREATE
        body = {"queue_name": "skittle",
                "ttl": ttl,
                "grace": grace}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    @ddt.data(-1, 59, 43201)
    def test_unacceptable_new_ttl(self, ttl):
        claim = self._get_a_claim()

        action = consts.CLAIM_UPDATE
        body = {"queue_name": "skittle",
                "claim_id": claim['body']['claim_id'],
                "ttl": ttl}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    def test_default_ttl_and_grace(self):
        action = consts.CLAIM_CREATE
        body = {"queue_name": "skittle"}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(201, resp['headers']['status'])

        action = consts.CLAIM_GET
        body = {"queue_name": "skittle",
                "claim_id": resp['body']['claim_id']}

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])

        self.assertEqual(200, resp['headers']['status'])
        self.assertEqual(self.defaults.claim_ttl, resp['body']['ttl'])

    def test_lifecycle(self):
        # First, claim some messages
        action = consts.CLAIM_CREATE
        body = {"queue_name": "skittle",
                "ttl": 100,
                "grace": 60}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(201, resp['headers']['status'])
        claimed_messages = resp['body']['messages']
        claim_id = resp['body']['claim_id']

        # No more messages to claim
        body = {"queue_name": "skittle",
                "ttl": 100,
                "grace": 60}

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

        # Listing messages, by default, won't include claimed, will echo
        action = consts.MESSAGE_LIST
        body = {"queue_name": "skittle",
                "echo": True}

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])
        self.assertEqual([], resp['body']['messages'])

        # Listing messages, by default, won't include claimed, won't echo

        body = {"queue_name": "skittle",
                "echo": False}

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])
        self.assertEqual([], resp['body']['messages'])

        # List messages, include_claimed, but don't echo

        body = {"queue_name": "skittle",
                "include_claimed": True,
                "echo": False}

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])
        self.assertEqual(resp['body']['messages'], [])

        # List messages with a different client-id and echo=false.
        # Should return some messages

        body = {"queue_name": "skittle",
                "echo": False}

        headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': self.project_id
        }

        req = test_utils.create_request(action, body, headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])

        # Include claimed messages this time, and echo

        body = {"queue_name": "skittle",
                "include_claimed": True,
                "echo": True}

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])
        self.assertEqual(len(claimed_messages), len(resp['body']['messages']))

        message_id_1 = resp['body']['messages'][0]['id']
        message_id_2 = resp['body']['messages'][1]['id']

        # Try to delete the message without submitting a claim_id
        action = consts.MESSAGE_DELETE
        body = {"queue_name": "skittle",
                "message_id": message_id_1}

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(403,  resp['headers']['status'])

        # Delete the message and its associated claim
        body = {"queue_name": "skittle",
                "message_id": message_id_1,
                "claim_id": claim_id}

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

        # Try to get it from the wrong project
        headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': 'someproject'
        }

        action = consts.MESSAGE_GET
        body = {"queue_name": "skittle",
                "message_id": message_id_2}
        req = test_utils.create_request(action, body, headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(404,  resp['headers']['status'])

        # Get the message
        action = consts.MESSAGE_GET
        body = {"queue_name": "skittle",
                "message_id": message_id_2}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])

        # Update the claim
        creation = timeutils.utcnow()
        action = consts.CLAIM_UPDATE
        body = {"queue_name": "skittle",
                "ttl": 60,
                "grace": 60,
                "claim_id": claim_id}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

        # Get the claimed messages (again)
        action = consts.CLAIM_GET
        body = {"queue_name": "skittle",
                "claim_id": claim_id}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        query = timeutils.utcnow()
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])
        self.assertEqual(60, resp['body']['ttl'])

        message_id_3 = resp['body']['messages'][0]['id']

        estimated_age = timeutils.delta_seconds(creation, query)
        # The claim's age should be 0 at this moment. But in some unexpected
        # case, such as slow test, the age maybe larger than 0. Just skip
        # asserting if so.
        if resp['body']['age'] == 0:
            self.assertGreater(estimated_age, resp['body']['age'])

        # Delete the claim
        action = consts.CLAIM_DELETE
        body = {"queue_name": "skittle",
                "claim_id": claim_id}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

        # Try to delete a message with an invalid claim ID
        action = consts.MESSAGE_DELETE
        body = {"queue_name": "skittle",
                "message_id": message_id_3,
                "claim_id": claim_id}

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

        # Make sure it wasn't deleted!
        action = consts.MESSAGE_GET
        body = {"queue_name": "skittle",
                "message_id": message_id_2}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])

        # Try to get a claim that doesn't exist
        action = consts.CLAIM_GET
        body = {"queue_name": "skittle",
                "claim_id": claim_id}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(404,  resp['headers']['status'])

        # Try to update a claim that doesn't exist
        action = consts.CLAIM_UPDATE
        body = {"queue_name": "skittle",
                "ttl": 60,
                "grace": 60,
                "claim_id": claim_id}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(404,  resp['headers']['status'])

    def test_post_claim_nonexistent_queue(self):
        action = consts.CLAIM_CREATE
        body = {"queue_name": "nonexistent",
                "ttl": 100,
                "grace": 60}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

    def test_get_claim_nonexistent_queue(self):
        action = consts.CLAIM_GET
        body = {"queue_name": "nonexistent",
                "claim_id": "aaabbbba"}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(404,  resp['headers']['status'])

    def _get_a_claim(self):
        action = consts.CLAIM_CREATE
        body = {"queue_name": "skittle",
                "ttl": 100,
                "grace": 60}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(201, resp['headers']['status'])

        return resp

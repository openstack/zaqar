# Copyright (c) 2015 Red Hat, Inc.
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

import datetime
import json

import ddt
import mock
from oslo_utils import timeutils
from oslo_utils import uuidutils
import six
from testtools import matchers

from zaqar.common import consts
from zaqar.tests.unit.transport.websocket import base
from zaqar.tests.unit.transport.websocket import utils as test_utils
from zaqar.transport import validation


@ddt.ddt
class MessagesBaseTest(base.V2Base):

    config_file = "websocket_mongodb.conf"

    def setUp(self):
        super(MessagesBaseTest, self).setUp()
        self.protocol = self.transport.factory()

        self.default_message_ttl = 3600

        self.project_id = '7e55e1a7e'
        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': self.project_id
        }

        body = {"queue_name": "kitkat"}
        req = test_utils.create_request(consts.QUEUE_CREATE,
                                        body, self.headers)

        with mock.patch.object(self.protocol, 'sendMessage') as msg_mock:
            self.protocol.onMessage(req, False)
            resp = json.loads(msg_mock.call_args[0][0])
            self.assertEqual(201, resp['headers']['status'])

    def tearDown(self):
        super(MessagesBaseTest, self).tearDown()
        body = {"queue_name": "kitkat"}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(consts.QUEUE_DELETE,
                                        body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

    def _test_post(self, sample_messages, in_binary=False):
        body = {"queue_name": "kitkat",
                "messages": sample_messages}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        dumps, loads, create_req = test_utils.get_pack_tools(binary=in_binary)

        req = create_req(consts.MESSAGE_POST, body, self.headers)

        self.protocol.onMessage(req, in_binary)

        resp = loads(send_mock.call_args[0][0])
        self.assertEqual(201, resp['headers']['status'])
        self.msg_ids = resp['body']['message_ids']
        self.assertEqual(len(sample_messages), len(self.msg_ids))

        lookup = dict([(m['ttl'], m['body']) for m in sample_messages])

        # Test GET on the message resource directly
        # NOTE(cpp-cabrera): force the passing of time to age a message
        timeutils_utcnow = 'oslo_utils.timeutils.utcnow'
        now = timeutils.utcnow() + datetime.timedelta(seconds=10)
        with mock.patch(timeutils_utcnow) as mock_utcnow:
            mock_utcnow.return_value = now
            for msg_id in self.msg_ids:
                headers = self.headers.copy()
                headers['X-Project-ID'] = '777777'
                # Wrong project ID
                action = consts.MESSAGE_GET
                body = {"queue_name": "kitkat",
                        "message_id": msg_id}

                req = create_req(action, body, headers)

                self.protocol.onMessage(req, in_binary)

                resp = loads(send_mock.call_args[0][0])
                self.assertEqual(404, resp['headers']['status'])

                # Correct project ID
                req = create_req(action, body, self.headers)

                self.protocol.onMessage(req, in_binary)

                resp = loads(send_mock.call_args[0][0])
                self.assertEqual(200, resp['headers']['status'])

                # Check message properties
                message = resp['body']['messages']
                self.assertEqual(lookup[message['ttl']], message['body'])
                self.assertEqual(msg_id, message['id'])

                # no negative age
                # NOTE(cpp-cabrera): testtools lacks
                # GreaterThanEqual on py26
                self.assertThat(message['age'],
                                matchers.GreaterThan(-1))

        # Test bulk GET
        action = consts.MESSAGE_GET_MANY
        body = {"queue_name": "kitkat",
                "message_ids": self.msg_ids}
        req = create_req(action, body, self.headers)

        self.protocol.onMessage(req, in_binary)

        resp = loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])
        expected_ttls = set(m['ttl'] for m in sample_messages)
        actual_ttls = set(m['ttl'] for m in resp['body']['messages'])
        self.assertFalse(expected_ttls - actual_ttls)
        actual_ids = set(m['id'] for m in resp['body']['messages'])
        self.assertFalse(set(self.msg_ids) - actual_ids)

    def test_exceeded_payloads(self):
        # Get a valid message id
        resp = self._post_messages("kitkat")
        msg_id = resp['body']['message_ids']

        # Bulk GET restriction
        get_msg_ids = msg_id * 21
        action = consts.MESSAGE_GET_MANY
        body = {"queue_name": "kitkat",
                "message_ids": get_msg_ids}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

        # Listing restriction
        body['limit'] = 21
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

        # Bulk deletion restriction
        del_msg_ids = msg_id * 22
        action = consts.MESSAGE_GET_MANY
        body = {"queue_name": "kitkat",
                "message_ids": del_msg_ids}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    @ddt.data(True, False)
    def test_post_single(self, in_binary):
        sample_messages = [
            {'body': {'key': 'value'}, 'ttl': 200},
        ]

        self._test_post(sample_messages, in_binary=in_binary)

    @ddt.data(True, False)
    def test_post_multiple(self, in_binary):
        sample_messages = [
            {'body': 239, 'ttl': 100},
            {'body': {'key': 'value'}, 'ttl': 200},
            {'body': [1, 3], 'ttl': 300},
        ]

        self._test_post(sample_messages, in_binary=in_binary)

    def test_post_optional_ttl(self):
        messages = [{'body': 239},
                    {'body': {'key': 'value'}, 'ttl': 200}]

        action = consts.MESSAGE_POST
        body = {"queue_name": "kitkat",
                "messages": messages}
        req = test_utils.create_request(action, body, self.headers)

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(201, resp['headers']['status'])
        msg_id = resp['body']['message_ids'][0]

        action = consts.MESSAGE_GET
        body = {"queue_name": "kitkat", "message_id": msg_id}

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])
        self.assertEqual(self.default_message_ttl,
                         resp['body']['messages']['ttl'])

    def test_post_to_non_ascii_queue(self):
        queue_name = u'non-ascii-n\u0153me'

        if six.PY2:
            queue_name = queue_name.encode('utf-8')

        resp = self._post_messages(queue_name)
        self.assertEqual(400, resp['headers']['status'])

    def test_post_with_long_queue_name(self):
        # NOTE(kgriffs): This test verifies that routes with
        # embedded queue name params go through the validation
        # hook, regardless of the target resource.

        queue_name = 'v' * validation.QUEUE_NAME_MAX_LEN

        resp = self._post_messages(queue_name)
        self.assertEqual(201, resp['headers']['status'])

        queue_name += 'v'
        resp = self._post_messages(queue_name)
        self.assertEqual(400, resp['headers']['status'])

    def test_post_to_missing_queue(self):
        queue_name = 'nonexistent'
        resp = self._post_messages(queue_name)
        self.assertEqual(201, resp['headers']['status'])

    def test_post_invalid_ttl(self):
        sample_messages = [
            {'body': {'key': 'value'}, 'ttl': '200'},
        ]

        action = consts.MESSAGE_POST
        body = {"queue_name": "kitkat",
                "messages": sample_messages}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        send_mock = send_mock.start()

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])
        self.assertEqual(
            'Bad request. The value of the "ttl" field must be a int.',
            resp['body']['exception'])

    def test_post_no_body(self):
        sample_messages = [
            {'ttl': 200},
        ]

        action = consts.MESSAGE_POST
        body = {"queue_name": "kitkat",
                "messages": sample_messages}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        send_mock = send_mock.start()

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])
        self.assertEqual(
            'Bad request. Missing "body" field.', resp['body']['exception'])

    def test_get_from_missing_queue(self):
        action = consts.MESSAGE_LIST
        body = {"queue_name": "anothernonexistent"}
        req = test_utils.create_request(action, body, self.headers)

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])
        self.assertEqual([], resp['body']['messages'])

    @ddt.data('', '0xdeadbeef', '550893e0-2b6e-11e3-835a-5cf9dd72369')
    def test_bad_client_id(self, text_id):
        action = consts.MESSAGE_POST
        body = {
            "queue_name": "kinder",
            "messages": [{"ttl": 60,
                          "body": ""}]
        }
        headers = {
            'Client-ID': text_id,
            'X-Project-ID': self.project_id
        }

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

        action = consts.MESSAGE_GET
        body = {
            "queue_name": "kinder",
            "limit": 3,
            "echo": True
        }

        req = test_utils.create_request(action, body, headers)
        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    @ddt.data(None, '[', '[]', '{}', '.')
    def test_post_bad_message(self, document):
        action = consts.MESSAGE_POST
        body = {
            "queue_name": "kinder",
            "messages": document
        }

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    @ddt.data(-1, 59, 1209601)
    def test_unacceptable_ttl(self, ttl):
        action = consts.MESSAGE_POST
        body = {"queue_name": "kinder",
                "messages": [{"ttl": ttl, "body": ""}]}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    def test_exceeded_message_posting(self):
        # Total (raw request) size
        document = [{'body': "some body", 'ttl': 100}] * 8000
        action = consts.MESSAGE_POST
        body = {
            "queue_name": "kinder",
            "messages": document
        }

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    @ddt.data('{"overflow": 9223372036854775808}',
              '{"underflow": -9223372036854775809}')
    def test_unsupported_json(self, document):
        action = consts.MESSAGE_POST
        body = {
            "queue_name": "fizz",
            "messages": document
        }

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    def test_delete(self):
        resp = self._post_messages("tofi")
        msg_id = resp['body']['message_ids'][0]

        action = consts.MESSAGE_GET
        body = {"queue_name": "tofi",
                "message_id": msg_id}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])

        # Delete queue
        action = consts.MESSAGE_DELETE
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

        # Get non existent queue
        action = consts.MESSAGE_GET
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(404, resp['headers']['status'])

        # Safe to delete non-existing ones
        action = consts.MESSAGE_DELETE
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

    def test_bulk_delete(self):
        resp = self._post_messages("nerds", repeat=5)
        msg_ids = resp['body']['message_ids']

        action = consts.MESSAGE_DELETE_MANY
        body = {"queue_name": "nerds",
                "message_ids": msg_ids}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

        action = consts.MESSAGE_GET
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

        # Safe to delete non-existing ones
        action = consts.MESSAGE_DELETE_MANY
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

        # Even after the queue is gone
        action = consts.QUEUE_DELETE
        body = {"queue_name": "nerds"}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

        action = consts.MESSAGE_DELETE_MANY
        body = {"queue_name": "nerds",
                "message_ids": msg_ids}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(204, resp['headers']['status'])

    def test_pop_delete(self):
        self._post_messages("kitkat", repeat=5)

        action = consts.MESSAGE_DELETE_MANY
        body = {"queue_name": "kitkat", "pop": 2}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])
        self.assertEqual(2, len(resp['body']['messages']))
        self.assertEqual(239, resp['body']['messages'][0]['body'])
        self.assertEqual(239, resp['body']['messages'][1]['body'])

    def test_get_nonexistent_message_404s(self):
        action = consts.MESSAGE_GET
        body = {"queue_name": "notthere",
                "message_id": "a"}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(404, resp['headers']['status'])

    def test_get_multiple_invalid_messages_404s(self):
        action = consts.MESSAGE_GET_MANY
        body = {"queue_name": "notnotthere",
                "message_ids": ["a", "b", "c"]}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])

    def test_delete_multiple_invalid_messages_204s(self):
        action = consts.MESSAGE_DELETE
        body = {"queue_name": "yetanothernotthere",
                "message_ids": ["a", "b", "c"]}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    def _post_messages(self, queue_name, repeat=1):
        messages = [{'body': 239, 'ttl': 300}] * repeat

        action = consts.MESSAGE_POST
        body = {"queue_name": queue_name,
                "messages": messages}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        return json.loads(send_mock.call_args[0][0])

    def test_invalid_request(self):
        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        self.protocol.onMessage('foo', False)
        self.assertEqual(1, send_mock.call_count)
        response = json.loads(send_mock.call_args[0][0])
        self.assertIn('error', response['body'])
        self.assertEqual({'status': 400}, response['headers'])
        self.assertEqual(
            {'action': None, 'api': 'v2', 'body': {}, 'headers': {}},
            response['request'])

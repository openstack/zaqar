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
import uuid

import ddt
import mock
from oslo_utils import timeutils
import six
from testtools import matchers

from zaqar.tests.unit.transport.websocket import base
from zaqar.tests.unit.transport.websocket import utils as test_utils
from zaqar.transport import validation


@ddt.ddt
class MessagesBaseTest(base.V1_1Base):

    config_file = "websocket_mongodb.conf"

    def setUp(self):
        super(MessagesBaseTest, self).setUp()
        self.protocol = self.transport.factory()

        self.default_message_ttl = 3600

        self.project_id = '7e55e1a7e'
        self.headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': self.project_id
        }

        action = "queue_create"
        body = {"queue_name": "kitkat"}
        req = test_utils.create_request(action, body, self.headers)

        with mock.patch.object(self.protocol, 'sendMessage') as msg_mock:
            self.protocol.onMessage(req, False)
            resp = json.loads(msg_mock.call_args[0][0])
            self.assertEqual(resp['headers']['status'], 201)

    def tearDown(self):
        super(MessagesBaseTest, self).tearDown()
        action = "queue_delete"
        body = {"queue_name": "kitkat"}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 204)

    def _test_post(self, sample_messages):
        action = "message_post"
        body = {"queue_name": "kitkat",
                "messages": sample_messages}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 201)
        self.msg_ids = resp['body']['message_ids']
        self.assertEqual(len(self.msg_ids), len(sample_messages))

        lookup = dict([(m['ttl'], m['body']) for m in sample_messages])

        # Test GET on the message resource directly
        # NOTE(cpp-cabrera): force the passing of time to age a message
        timeutils_utcnow = 'zaqar.openstack.common.timeutils.utcnow'
        now = timeutils.utcnow() + datetime.timedelta(seconds=10)
        with mock.patch(timeutils_utcnow) as mock_utcnow:
            mock_utcnow.return_value = now
            for msg_id in self.msg_ids:
                headers = self.headers.copy()
                headers['X-Project-ID'] = '777777'
                # Wrong project ID
                action = "message_get"
                body = {"queue_name": "kitkat",
                        "message_id": msg_id}

                req = test_utils.create_request(action, body, headers)

                self.protocol.onMessage(req, False)

                resp = json.loads(send_mock.call_args[0][0])
                self.assertEqual(resp['headers']['status'], 404)

                # Correct project ID
                req = test_utils.create_request(action, body, self.headers)

                self.protocol.onMessage(req, False)

                resp = json.loads(send_mock.call_args[0][0])
                self.assertEqual(resp['headers']['status'], 200)

                # Check message properties
                message = resp['body']['messages']
                self.assertEqual(message['body'], lookup[message['ttl']])
                self.assertEqual(message['id'], msg_id)

                # no negative age
                # NOTE(cpp-cabrera): testtools lacks
                # GreaterThanEqual on py26
                self.assertThat(message['age'],
                                matchers.GreaterThan(-1))

        # Test bulk GET
        action = "message_get_many"
        body = {"queue_name": "kitkat",
                "message_ids": self.msg_ids}
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 200)
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
        action = "message_get_many"
        body = {"queue_name": "kitkat",
                "message_ids": get_msg_ids}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 400)

        # Listing restriction
        body['limit'] = 21
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 400)

        # Bulk deletion restriction
        del_msg_ids = msg_id * 22
        action = "message_get_many"
        body = {"queue_name": "kitkat",
                "message_ids": del_msg_ids}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 400)

    def test_post_single(self):
        sample_messages = [
            {'body': {'key': 'value'}, 'ttl': 200},
        ]

        self._test_post(sample_messages)

    def test_post_multiple(self):
        sample_messages = [
            {'body': 239, 'ttl': 100},
            {'body': {'key': 'value'}, 'ttl': 200},
            {'body': [1, 3], 'ttl': 300},
        ]

        self._test_post(sample_messages)

    def test_post_optional_ttl(self):
        messages = [{'body': 239},
                    {'body': {'key': 'value'}, 'ttl': 200}]

        action = "message_post"
        body = {"queue_name": "kitkat",
                "messages": messages}
        req = test_utils.create_request(action, body, self.headers)

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 201)
        msg_id = resp['body']['message_ids'][0]

        action = "message_get"
        body = {"queue_name": "kitkat", "message_id": msg_id}

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 200)
        self.assertEqual(self.default_message_ttl,
                         resp['body']['messages']['ttl'])

    def test_post_to_non_ascii_queue(self):
        queue_name = u'non-ascii-n\u0153me'

        if six.PY2:
            queue_name = queue_name.encode('utf-8')

        resp = self._post_messages(queue_name)
        self.assertEqual(resp['headers']['status'], 400)

    def test_post_with_long_queue_name(self):
        # NOTE(kgriffs): This test verifies that routes with
        # embedded queue name params go through the validation
        # hook, regardless of the target resource.

        queue_name = 'v' * validation.QUEUE_NAME_MAX_LEN

        resp = self._post_messages(queue_name)
        self.assertEqual(resp['headers']['status'], 201)

        queue_name += 'v'
        resp = self._post_messages(queue_name)
        self.assertEqual(resp['headers']['status'], 400)

    def test_post_to_missing_queue(self):
        queue_name = 'nonexistent'
        resp = self._post_messages(queue_name)
        self.assertEqual(resp['headers']['status'], 201)

    def test_post_invalid_ttl(self):
        sample_messages = [
            {'body': {'key': 'value'}, 'ttl': '200'},
        ]

        action = "message_post"
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

        action = "message_post"
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
        action = "message_list"
        body = {"queue_name": "anothernonexistent"}
        req = test_utils.create_request(action, body, self.headers)

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 200)
        self.assertEqual(resp['body']['messages'], [])

    @ddt.data('', '0xdeadbeef', '550893e0-2b6e-11e3-835a-5cf9dd72369')
    def test_bad_client_id(self, text_id):
        action = "message_post"
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
        self.assertEqual(resp['headers']['status'], 400)

        action = "message_get"
        body = {
            "queue_name": "kinder",
            "limit": 3,
            "echo": True
        }

        req = test_utils.create_request(action, body, headers)
        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 400)

    @ddt.data(None, '[', '[]', '{}', '.')
    def test_post_bad_message(self, document):
        action = "message_post"
        body = {
            "queue_name": "kinder",
            "messages": document
        }

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 400)

    @ddt.data(-1, 59, 1209601)
    def test_unacceptable_ttl(self, ttl):
        action = "message_post"
        body = {"queue_name": "kinder",
                "messages": [{"ttl": ttl, "body": ""}]}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 400)

    def test_exceeded_message_posting(self):
        # Total (raw request) size
        document = [{'body': "some body", 'ttl': 100}] * 8000
        action = "message_post"
        body = {
            "queue_name": "kinder",
            "messages": document
        }

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 400)

    @ddt.data('{"overflow": 9223372036854775808}',
              '{"underflow": -9223372036854775809}')
    def test_unsupported_json(self, document):
        action = "message_post"
        body = {
            "queue_name": "fizz",
            "messages": document
        }

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 400)

    def test_delete(self):
        resp = self._post_messages("tofi")
        msg_id = resp['body']['message_ids'][0]

        action = "message_get"
        body = {"queue_name": "tofi",
                "message_id": msg_id}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 200)

        # Delete queue
        action = "message_delete"
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 204)

        # Get non existent queue
        action = "message_get"
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 404)

        # Safe to delete non-existing ones
        action = "message_delete"
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 204)

    def test_bulk_delete(self):
        resp = self._post_messages("nerds", repeat=5)
        msg_ids = resp['body']['message_ids']

        action = "message_delete_many"
        body = {"queue_name": "nerds",
                "message_ids": msg_ids}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 204)

        action = "message_get"
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 400)

        # Safe to delete non-existing ones
        action = "message_delete_many"
        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 204)

        # Even after the queue is gone
        action = "queue_delete"
        body = {"queue_name": "nerds"}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 204)

        action = "message_delete_many"
        body = {"queue_name": "nerds",
                "message_ids": msg_ids}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 204)

    def test_get_nonexistent_message_404s(self):
        action = "message_get"
        body = {"queue_name": "notthere",
                "message_id": "a"}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 404)

    def test_get_multiple_invalid_messages_404s(self):
        action = "message_get_many"
        body = {"queue_name": "notnotthere",
                "message_ids": ["a", "b", "c"]}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 200)

    def test_delete_multiple_invalid_messages_204s(self):
        action = "message_delete"
        body = {"queue_name": "yetanothernotthere",
                "message_ids": ["a", "b", "c"]}

        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        req = test_utils.create_request(action, body, self.headers)

        self.protocol.onMessage(req, False)

        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(resp['headers']['status'], 400)

    def _post_messages(self, queue_name, repeat=1):
        messages = [{'body': 239, 'ttl': 300}] * repeat

        action = "message_post"
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
            {'action': None, 'api': 'v1.1', 'body': {}, 'headers': {}},
            response['request'])

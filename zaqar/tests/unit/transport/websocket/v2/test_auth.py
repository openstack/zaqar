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

import json

import ddt
from keystonemiddleware import auth_token
import mock

from oslo_utils import uuidutils
from zaqar.common import consts
from zaqar.common import urls
from zaqar.tests.unit.transport.websocket import base
from zaqar.tests.unit.transport.websocket import utils as test_utils


@ddt.ddt
class AuthTest(base.V2Base):
    config_file = "websocket_mongodb_keystone_auth.conf"

    def setUp(self):
        super(AuthTest, self).setUp()
        self.protocol = self.transport.factory()
        self.protocol.factory._secret_key = 'secret'

        self.default_message_ttl = 3600

        self.project_id = '7e55e1a7e'
        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': self.project_id
        }
        auth_mock = mock.patch.object(auth_token.AuthProtocol, '__call__')
        self.addCleanup(auth_mock.stop)
        self.auth = auth_mock.start()
        self.env = {'keystone.token_info': {
            'token': {'expires_at': '2035-08-05T15:16:33.603700+00:00'}}}

    def test_post(self):
        headers = self.headers.copy()
        headers['X-Auth-Token'] = 'mytoken1'
        req = json.dumps({'action': 'authenticate', 'headers': headers})

        msg_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(msg_mock.stop)
        msg_mock = msg_mock.start()
        self.protocol.onMessage(req, False)

        # Didn't send the response yet
        self.assertEqual(0, msg_mock.call_count)

        self.assertEqual(1, self.auth.call_count)
        responses = []
        self.protocol._auth_start(self.env, lambda x, y: responses.append(x))

        self.assertEqual(1, len(responses))
        self.assertEqual('200 OK', responses[0])

        # Check that the env is available to future requests
        req = json.dumps({'action': consts.MESSAGE_LIST,
                          'body': {'queue_name': 'myqueue'},
                          'headers': self.headers})
        process_request = mock.patch.object(self.protocol._handler,
                                            'process_request').start()
        process_request.return_value = self.protocol._handler.create_response(
            200, {})
        self.protocol.onMessage(req, False)
        self.assertEqual(1, process_request.call_count)
        self.assertEqual(self.env, process_request.call_args[0][0]._env)

    def test_post_between_auth(self):
        headers = self.headers.copy()
        headers['X-Auth-Token'] = 'mytoken1'
        req = json.dumps({'action': 'authenticate', 'headers': headers})

        msg_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(msg_mock.stop)
        msg_mock = msg_mock.start()
        self.protocol.onMessage(req, False)

        req = test_utils.create_request(consts.QUEUE_LIST, {}, self.headers)
        self.protocol.onMessage(req, False)

        self.assertEqual(1, msg_mock.call_count)
        resp = json.loads(msg_mock.call_args[0][0])
        self.assertEqual(403, resp['headers']['status'])

    def test_failed_auth(self):
        msg_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(msg_mock.stop)
        msg_mock = msg_mock.start()
        self.protocol._auth_in_binary = False
        self.protocol._auth_response('401 error', 'Failed')
        self.assertEqual(1, msg_mock.call_count)
        resp = json.loads(msg_mock.call_args[0][0])
        self.assertEqual(401, resp['headers']['status'])
        self.assertEqual('authenticate', resp['request']['action'])

    def test_reauth(self):
        headers = self.headers.copy()
        headers['X-Auth-Token'] = 'mytoken1'
        req = json.dumps({'action': 'authenticate', 'headers': headers})

        msg_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(msg_mock.stop)
        msg_mock = msg_mock.start()
        self.protocol.onMessage(req, False)

        self.assertEqual(1, self.auth.call_count)
        responses = []
        self.protocol._auth_start(self.env, lambda x, y: responses.append(x))

        self.assertEqual(1, len(responses))
        handle = self.protocol._deauth_handle
        self.assertIsNotNone(handle)

        headers = self.headers.copy()
        headers['X-Auth-Token'] = 'mytoken2'
        req = json.dumps({'action': 'authenticate', 'headers': headers})
        self.protocol.onMessage(req, False)
        self.protocol._auth_start(self.env, lambda x, y: responses.append(x))

        self.assertNotEqual(handle, self.protocol._deauth_handle)
        self.assertEqual(2, len(responses))
        self.assertIn('cancelled', repr(handle))
        self.assertNotIn('cancelled', repr(self.protocol._deauth_handle))

    def test_reauth_after_auth_failure(self):
        headers = self.headers.copy()
        headers['X-Auth-Token'] = 'wrong_token'
        req = json.dumps({'action': 'authenticate', 'headers': headers})

        msg_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(msg_mock.stop)
        msg_mock = msg_mock.start()
        # after authenticate failure, the _auth_app will be  None and the
        # request will raise 401 error.
        self.protocol.onMessage(req, False)
        self.protocol._auth_response('401 error', 'Failed')
        resp = json.loads(msg_mock.call_args[0][0])

        self.assertEqual(401, resp['headers']['status'])
        self.assertEqual('authenticate', resp['request']['action'])
        self.assertIsNone(self.protocol._auth_app)

        # try to authenticate again, "onMessage" should not return 403 because
        # that the _auth_app was cleaned after auth failure.
        headers['X-Auth-Token'] = 'mytoken'
        req = json.dumps({'action': 'authenticate', 'headers': headers})
        self.protocol.onMessage(req, False)

        self.protocol._auth_response('200 OK', 'authenticate success')
        resp = json.loads(msg_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])

    @ddt.data(True, False)
    def test_auth_response_serialization_format(self, in_binary):
        dumps, loads, create_req = test_utils.get_pack_tools(binary=in_binary)
        headers = self.headers.copy()
        headers['X-Auth-Token'] = 'mytoken1'
        req = create_req("authenticate", {}, headers)

        msg_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(msg_mock.stop)
        msg_mock = msg_mock.start()
        # Depending on onMessage method's second argument, auth response should
        # be in binary or text format.
        self.protocol.onMessage(req, in_binary)
        self.assertEqual(in_binary, self.protocol._auth_in_binary)
        self.protocol._auth_response('401 error', 'Failed')
        self.assertEqual(1, msg_mock.call_count)
        resp = loads(msg_mock.call_args[0][0])
        self.assertEqual(401, resp['headers']['status'])

    def test_signed_url(self):
        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        data = urls.create_signed_url(
            'secret', ['/v2/queues/myqueue/messages'], project=self.project_id,
            methods=['GET'])

        headers = self.headers.copy()
        headers.update({
            'URL-Signature': data['signature'],
            'URL-Expires': data['expires'],
            'URL-Methods': ['GET'],
            'URL-Paths': ['/v2/queues/myqueue/messages']
        })
        req = json.dumps({'action': consts.MESSAGE_LIST,
                          'body': {'queue_name': 'myqueue'},
                          'headers': headers})
        self.protocol.onMessage(req, False)

        self.assertEqual(1, send_mock.call_count)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(200, resp['headers']['status'])

    def test_signed_url_wrong_queue(self):
        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        data = urls.create_signed_url(
            'secret', ['/v2/queues/myqueue/messages'], project=self.project_id,
            methods=['GET'])

        headers = self.headers.copy()
        headers.update({
            'URL-Signature': data['signature'],
            'URL-Expires': data['expires'],
            'URL-Methods': ['GET'],
            'URL-Paths': ['/v2/queues/otherqueue/messages']
        })
        req = json.dumps({'action': consts.MESSAGE_LIST,
                          'body': {'queue_name': 'otherqueue'},
                          'headers': headers})
        self.protocol.onMessage(req, False)

        self.assertEqual(1, send_mock.call_count)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(403, resp['headers']['status'])

    def test_signed_url_wrong_method(self):
        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        data = urls.create_signed_url(
            'secret', ['/v2/queues/myqueue/messages'], project=self.project_id,
            methods=['GET'])

        headers = self.headers.copy()
        headers.update({
            'URL-Signature': data['signature'],
            'URL-Expires': data['expires'],
            'URL-Methods': ['GET'],
            'URL-Paths': ['/v2/queues/myqueue/messages']
        })
        req = json.dumps({'action': consts.MESSAGE_DELETE,
                          'body': {'queue_name': 'myqueue',
                                   'message_id': '123'},
                          'headers': headers})
        self.protocol.onMessage(req, False)

        self.assertEqual(1, send_mock.call_count)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(403, resp['headers']['status'])

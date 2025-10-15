# Copyright 2016 OpenStack Foundation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest import mock

import ddt
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

import zaqar
from zaqar.tests.unit.transport.websocket import base
from zaqar.tests.unit.transport.websocket import utils as test_utils


@ddt.ddt
class TestMessagingProtocol(base.TestBase):
    config_file = "websocket_mongodb.conf"

    def setUp(self):
        super().setUp()
        self.protocol = self.transport.factory()
        self.project_id = 'protocol-test'
        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': self.project_id
        }

    def test_on_message_with_invalid_input(self):
        payload = '\ufeff'
        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        self.protocol.onMessage(payload, False)
        resp = jsonutils.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

        payload = "123"

        self.protocol.onMessage(payload, False)
        resp = jsonutils.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

    def test_on_message_with_invalid_input_binary(self):
        dumps, loads, create_req = test_utils.get_pack_tools(binary=True)
        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        # Test error response, when the request can't be deserialized.
        req = "123"
        self.protocol.onMessage(req, True)
        resp = loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])
        self.assertIn('Can\'t decode binary', resp['body']['error'])

        # Test error response, when request body is not a dictionary.
        req = dumps("Apparently, I'm not a dictionary")
        self.protocol.onMessage(req, True)
        resp = loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])
        self.assertIn('Unexpected body type. Expected dict',
                      resp['body']['error'])

        # Test error response, when validation fails.
        action = 'queue_glorify'
        body = {}
        req = create_req(action, body, self.headers)
        self.protocol.onMessage(req, True)
        resp = loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])
        self.assertEqual('queue_glorify is not a valid action',
                         resp['body']['error'])

    @ddt.data(True, False)
    def test_on_message_with_input_in_different_format(self, in_binary):
        dumps, loads, create_req = test_utils.get_pack_tools(binary=in_binary)
        action = 'queue_get'
        body = {'queue_name': 'beautiful-non-existing-queue'}
        req = create_req(action, body, self.headers)
        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock
        self.protocol.onMessage(req, in_binary)
        arg = send_mock.call_args[0][0]
        resp = loads(arg)
        self.assertEqual(200, resp['headers']['status'])

    @mock.patch.object(zaqar.transport.websocket.factory, 'ProtocolFactory')
    def test_ipv6_escaped(self, mock_pf):
        delattr(self.transport, '_lazy_factory')
        self.transport.factory()
        self.assertEqual('ws://127.0.0.1:9000', mock_pf.mock_calls[0][1][0])

        mock_pf.reset_mock()
        with mock.patch.object(self.transport._ws_conf, 'bind', "1::4"):
            delattr(self.transport, '_lazy_factory')
            self.transport.factory()
            self.assertEqual('ws://[1::4]:9000', mock_pf.mock_calls[0][1][0])

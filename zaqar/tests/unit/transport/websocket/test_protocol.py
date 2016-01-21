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

import json

import mock

from zaqar.tests.unit.transport.websocket import base


class TestMessagingProtocol(base.TestBase):
    config_file = "websocket_mongodb.conf"

    def setUp(self):
        super(TestMessagingProtocol, self).setUp()
        self.protocol = self.transport.factory()
        self.defaults = self.api.get_defaults()

    def tearDown(self):
        super(TestMessagingProtocol, self).tearDown()

    def test_on_mesage_with_invalid_input(self):
        payload = u'\ufeff'
        send_mock = mock.Mock()
        self.protocol.sendMessage = send_mock

        self.protocol.onMessage(payload, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

        payload = "123"

        self.protocol.onMessage(payload, False)
        resp = json.loads(send_mock.call_args[0][0])
        self.assertEqual(400, resp['headers']['status'])

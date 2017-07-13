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
from oslo_utils import uuidutils

from testtools import testcase
import websocket

from zaqar.tests.functional import base


class TestQueues(base.V1_1FunctionalTestBase):

    config_file = 'websocket_mongodb.conf'
    server_class = base.ZaqarServer

    def setUp(self):
        if not base._TEST_INTEGRATION:
            raise testcase.TestSkipped('Only run in integration mode')
        super(TestQueues, self).setUp()
        self.project_id = uuidutils.generate_uuid()
        self.headers = {'Client-ID': uuidutils.generate_uuid(),
                        'X-Project-ID': self.project_id}
        self.client = websocket.create_connection('ws://localhost:9000/')
        self.addCleanup(self.client.close)

    def test_list_empty(self):
        self.client.send(
            json.dumps({'action': 'queue_list', 'headers': self.headers}))
        response = json.loads(self.client.recv())
        self.assertEqual(
            {'body': {'queues': []},
             'headers': {'status': 200},
             'request': {'action': 'queue_list', 'body': {}, 'api': 'v2',
                         'headers': self.headers}},
            response)

    def test_list(self):
        self.client.send(
            json.dumps({'action': 'queue_create',
                        'body': {'queue_name': 'my_queue'},
                        'headers': self.headers}))
        response = json.loads(self.client.recv())
        self.assertEqual(
            {'body': 'Queue my_queue created.',
             'headers': {'status': 201},
             'request': {'action': 'queue_create',
                         'body': {'queue_name': 'my_queue'}, 'api': 'v2',
                         'headers': self.headers}},
            response)
        self.client.send(
            json.dumps({'action': 'queue_list', 'headers': self.headers}))
        response = json.loads(self.client.recv())
        self.assertEqual(
            {'body': {'queues': [{'name': 'my_queue'}]},
             'headers': {'status': 200},
             'request': {'action': 'queue_list', 'body': {}, 'api': 'v2',
                         'headers': self.headers}},
            response)

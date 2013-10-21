# Copyright (c) 2013 Rackspace, Inc.
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
import uuid

import falcon

import base  # noqa


class DefaultLimitsTest(base.TestBase):

    config_file = 'wsgi_sqlite_default_limits.conf'

    def setUp(self):
        super(DefaultLimitsTest, self).setUp()

        self.queue_path = '/v1/queues/q1'
        self.messages_path = self.queue_path + '/messages'
        self.claims_path = self.queue_path + '/claims'

        self.simulate_put(self.queue_path)

    def tearDown(self):
        self.simulate_delete(self.queue_path)
        super(DefaultLimitsTest, self).tearDown()

    def test_queue_listing(self):
        default_queue_paging = 1

        # 2 queues to list
        self.simulate_put('/v1/queues/q2')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        result = self.simulate_get('/v1/queues')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        queues = json.loads(result[0])['queues']
        self.assertEqual(len(queues), default_queue_paging)

        self.simulate_delete('/v1/queues/q2')

    def test_message_listing(self):
        default_message_paging = 2

        # 10 messages to list
        self.__prepare_messages(10)

        result = self.simulate_get(self.messages_path,
                                   headers={'Client-ID': str(uuid.uuid4())})

        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        messages = json.loads(result[0])['messages']
        self.assertEqual(len(messages), default_message_paging)

    def test_claim_creation(self):
        default_message_paging = 2

        # 5 messages to claim
        self.__prepare_messages(5)

        result = self.simulate_post(self.claims_path,
                                    body='{"ttl": 60, "grace": 60}')

        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        messages = json.loads(result[0])
        self.assertEqual(len(messages), default_message_paging)

    def __prepare_messages(self, count):
        doc = json.dumps([{'body': 239, 'ttl': 300}] * count)
        self.simulate_post(self.messages_path, body=doc,
                           headers={'Client-ID': 'poster'})

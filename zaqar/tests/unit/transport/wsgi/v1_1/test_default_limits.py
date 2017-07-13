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

import contextlib

import falcon
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from zaqar import storage
from zaqar.tests.unit.transport.wsgi import base


class TestDefaultLimits(base.V1_1Base):

    config_file = 'wsgi_mongodb_default_limits.conf'

    def setUp(self):
        super(TestDefaultLimits, self).setUp()

        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': '%s_' % uuidutils.generate_uuid()
        }
        self.queue_path = self.url_prefix + '/queues'
        self.q1_queue_path = self.queue_path + '/' + uuidutils.generate_uuid()
        self.messages_path = self.q1_queue_path + '/messages'
        self.claims_path = self.q1_queue_path + '/claims'

        self.simulate_put(self.q1_queue_path, headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def tearDown(self):
        self.simulate_delete(self.queue_path, headers=self.headers)
        super(TestDefaultLimits, self).tearDown()

    def test_queue_listing(self):
        # 2 queues to list
        self.simulate_put(self.queue_path + '/q2', headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        with self._prepare_queues(storage.DEFAULT_QUEUES_PER_PAGE + 1):
            result = self.simulate_get(self.queue_path, headers=self.headers)
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

            queues = jsonutils.loads(result[0])['queues']
            self.assertEqual(storage.DEFAULT_QUEUES_PER_PAGE, len(queues))

    def test_message_listing_different_id(self):
        self._prepare_messages(storage.DEFAULT_MESSAGES_PER_PAGE + 1)

        headers = self.headers.copy()
        headers['Client-ID'] = uuidutils.generate_uuid()
        result = self.simulate_get(self.messages_path,
                                   headers=headers,
                                   query_string='echo=false')

        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        messages = jsonutils.loads(result[0])['messages']
        self.assertEqual(storage.DEFAULT_MESSAGES_PER_PAGE, len(messages))

    def test_message_listing_same_id(self):
        self._prepare_messages(storage.DEFAULT_MESSAGES_PER_PAGE + 1)
        result = self.simulate_get(self.messages_path,
                                   headers=self.headers,
                                   query_string='echo=false')

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self._empty_message_list(result)

        self._prepare_messages(storage.DEFAULT_MESSAGES_PER_PAGE + 1)
        result = self.simulate_get(self.messages_path,
                                   headers=self.headers,
                                   query_string='echo=true')

        messages = jsonutils.loads(result[0])['messages']
        self.assertEqual(storage.DEFAULT_MESSAGES_PER_PAGE, len(messages))

    def test_claim_creation(self):
        self._prepare_messages(storage.DEFAULT_MESSAGES_PER_CLAIM + 1)

        result = self.simulate_post(self.claims_path,
                                    body='{"ttl": 60, "grace": 60}',
                                    headers=self.headers)

        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        messages = jsonutils.loads(result[0])['messages']
        self.assertEqual(storage.DEFAULT_MESSAGES_PER_CLAIM, len(messages))

    @contextlib.contextmanager
    def _prepare_queues(self, count):
        queue_paths = [self.queue_path + '/multi-{0}'.format(i)
                       for i in range(count)]

        for path in queue_paths:
            self.simulate_put(path, headers=self.headers)
            self.assertEqual(falcon.HTTP_201, self.srmock.status)

        yield

        for path in queue_paths:
            self.simulate_delete(path, headers=self.headers)

    def _prepare_messages(self, count):
        doc = {'messages': [{'body': 239, 'ttl': 300}] * count}
        body = jsonutils.dumps(doc)
        self.simulate_post(self.messages_path, body=body,
                           headers=self.headers)

        self.assertEqual(falcon.HTTP_201, self.srmock.status)

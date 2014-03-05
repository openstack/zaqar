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
import json
import uuid

import falcon

from . import base  # noqa

from marconi.queues import storage


class TestDefaultLimits(base.TestBase):

    config_file = 'wsgi_sqlalchemy_default_limits.conf'

    def setUp(self):
        super(TestDefaultLimits, self).setUp()

        self.queue_path = self.url_prefix + '/queues'
        self.q1_queue_path = self.queue_path + '/q1'
        self.messages_path = self.q1_queue_path + '/messages'
        self.claims_path = self.q1_queue_path + '/claims'

        self.simulate_put(self.q1_queue_path)

    def tearDown(self):
        self.simulate_delete(self.queue_path)
        super(TestDefaultLimits, self).tearDown()

    def test_queue_listing(self):
        # 2 queues to list
        self.simulate_put(self.queue_path + '/q2')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        with self._prepare_queues(storage.DEFAULT_QUEUES_PER_PAGE + 1):
            result = self.simulate_get(self.queue_path)
            self.assertEqual(self.srmock.status, falcon.HTTP_200)

            queues = json.loads(result[0])['queues']
            self.assertEqual(len(queues), storage.DEFAULT_QUEUES_PER_PAGE)

    def test_message_listing(self):
        self._prepare_messages(storage.DEFAULT_MESSAGES_PER_PAGE + 1)

        result = self.simulate_get(self.messages_path,
                                   headers={'Client-ID': str(uuid.uuid4())})

        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        messages = json.loads(result[0])['messages']
        self.assertEqual(len(messages), storage.DEFAULT_MESSAGES_PER_PAGE)

    def test_claim_creation(self):
        self._prepare_messages(storage.DEFAULT_MESSAGES_PER_CLAIM + 1)

        result = self.simulate_post(self.claims_path,
                                    body='{"ttl": 60, "grace": 60}')

        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        messages = json.loads(result[0])
        self.assertEqual(len(messages), storage.DEFAULT_MESSAGES_PER_CLAIM)

    @contextlib.contextmanager
    def _prepare_queues(self, count):
        queue_paths = [self.queue_path + '/multi-{0}'.format(i)
                       for i in range(count)]

        for path in queue_paths:
            self.simulate_put(path)
            self.assertEqual(self.srmock.status, falcon.HTTP_201)

        yield

        for path in queue_paths:
            self.simulate_delete(path)

    def _prepare_messages(self, count):
        doc = json.dumps([{'body': 239, 'ttl': 300}] * count)
        self.simulate_post(self.messages_path, body=doc,
                           headers={'Client-ID': str(uuid.uuid4())})

        self.assertEqual(self.srmock.status, falcon.HTTP_201)

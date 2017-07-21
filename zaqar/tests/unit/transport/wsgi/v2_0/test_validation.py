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

import falcon

from oslo_utils import uuidutils
from zaqar.tests.unit.transport.wsgi import base


class TestValidation(base.V2Base):

    config_file = 'wsgi_mongodb_validation.conf'

    def setUp(self):
        super(TestValidation, self).setUp()

        self.project_id = '7e55e1a7e'

        self.queue_path = self.url_prefix + '/queues/noein'
        self.simulate_put(self.queue_path, self.project_id)

        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
        }

    def tearDown(self):
        self.simulate_delete(self.queue_path, self.project_id)
        super(TestValidation, self).tearDown()

    def test_metadata_deserialization(self):
        # Normal case
        self.simulate_put(self.queue_path,
                          self.project_id,
                          body='{"timespace": "Shangri-la"}')

        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Too long
        max_queue_metadata = 64

        doc_tmpl = '{{"Dragon Torc":"{0}"}}'
        doc_tmpl_ws = '{{ "Dragon Torc" : "{0}" }}'  # with whitespace
        envelope_length = len(doc_tmpl.format(''))

        for tmpl in doc_tmpl, doc_tmpl_ws:
            gen = '0' * (max_queue_metadata - envelope_length + 1)
            doc = tmpl.format(gen)
            self.simulate_put(self.queue_path,
                              self.project_id,
                              body=doc)

            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_message_deserialization(self):
        # Normal case
        body = '{"messages": [{"body": "Dragon Knights", "ttl": 100}]}'
        self.simulate_post(self.queue_path + '/messages',
                           self.project_id, body=body,
                           headers=self.headers)

        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # Both messages' size are too long
        max_messages_post_size = 256

        obj = {'a': 0, 'b': ''}
        envelope_length = len(json.dumps(obj, separators=(',', ':')))
        obj['b'] = 'x' * (max_messages_post_size - envelope_length + 1)

        for long_body in ('a' * (max_messages_post_size - 2 + 1), obj):
            doc = json.dumps([{'body': long_body, 'ttl': 100}])
            self.simulate_post(self.queue_path + '/messages',
                               self.project_id,
                               body=doc,
                               headers=self.headers)

            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_request_without_client_id(self):
        # No Client-ID in headers, it will raise 400 error.
        empty_headers = {}
        self.simulate_put(self.queue_path,
                          self.project_id,
                          body='{"timespace": "Shangri-la"}',
                          headers=empty_headers)

    def test_subscription_ttl(self):
        # Normal case
        body = '{"subscriber": "http://trigger.she", "ttl": 100, "options":{}}'
        self.simulate_post(self.queue_path + '/subscriptions',
                           self.project_id, body=body,
                           headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # Very big TTL
        body = ('{"subscriber": "http://a.c", "ttl": 99999999999999999'
                ', "options":{}}')
        self.simulate_post(self.queue_path + '/subscriptions',
                           self.project_id, body=body,
                           headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_queue_metadata_putting(self):
        # Test _default_message_ttl
        # TTL normal case
        queue_1 = self.url_prefix + '/queues/queue1'
        self.simulate_put(queue_1,
                          self.project_id,
                          body='{"_default_message_ttl": 60}')
        self.addCleanup(self.simulate_delete, queue_1, self.project_id,
                        headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # TTL under min
        self.simulate_put(queue_1,
                          self.project_id,
                          body='{"_default_message_ttl": 59}')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # TTL over max
        self.simulate_put(queue_1,
                          self.project_id,
                          body='{"_default_message_ttl": 1209601}')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Test _max_messages_post_size
        # Size normal case
        queue_2 = self.url_prefix + '/queues/queue2'
        self.simulate_put(queue_2,
                          self.project_id,
                          body='{"_max_messages_post_size": 255}')
        self.addCleanup(self.simulate_delete, queue_2, self.project_id,
                        headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # Size over max
        self.simulate_put(queue_2,
                          self.project_id,
                          body='{"_max_messages_post_size": 257}')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # _dead_letter_queue_messages_ttl is not integer
        self.simulate_put(queue_2,
                          self.project_id,
                          body='{"_dead_letter_queue_messages_ttl": "123"}')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # _max_claim_count is not integer
        self.simulate_put(queue_2,
                          self.project_id,
                          body='{"_max_claim_count": "123"}')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # _dead_letter_queue_messages_ttl is out of range
        self.simulate_put(queue_2,
                          self.project_id,
                          body='{"_dead_letter_queue_messages_ttl": 59}')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_queue_patching(self):
        headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'Content-Type': "application/openstack-messaging-v2.0-json-patch"
        }

        # Wrong JSON pointer
        self.simulate_patch(self.queue_path,
                            self.project_id,
                            headers=headers,
                            body='[{"op":"add","path":"/a","value":2}]')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Wrong op
        self.simulate_patch(self.queue_path,
                            self.project_id,
                            headers=headers,
                            body='[{"op":"a","path":"/metadata/a","value":2}]')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_patch(self.queue_path,
                            self.project_id,
                            headers=headers,
                            body='[{"op":"add","path":"/metadata/a",'
                            '"value":2}]')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_queue_purge(self):
        # Wrong key
        queue_1 = self.url_prefix + '/queues/queue1/purge'
        self.simulate_post(queue_1,
                           self.project_id,
                           body='{"wrong_key": ["messages"]}')
        self.addCleanup(self.simulate_delete, queue_1, self.project_id,
                        headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Wrong value
        self.simulate_post(queue_1,
                           self.project_id,
                           body='{"resource_types": ["wrong_value"]}')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Correct input
        self.simulate_post(queue_1,
                           self.project_id,
                           body='{"resource_types": ["messages"]}')
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

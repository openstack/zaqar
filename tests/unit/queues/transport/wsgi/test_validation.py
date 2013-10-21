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


class ValidationTest(base.TestBase):

    config_file = 'wsgi_sqlite_validation.conf'

    def setUp(self):
        super(ValidationTest, self).setUp()

        self.project_id = '7e55e1a7e'
        self.queue_path = '/v1/queues/noein'

        self.simulate_put(self.queue_path, self.project_id)

        self.headers = {
            'Client-ID': str(uuid.uuid4()),
        }

    def tearDown(self):
        self.simulate_delete(self.queue_path, self.project_id)
        super(ValidationTest, self).tearDown()

    def test_metadata_deserialization(self):
        # Normal case
        self.simulate_put(self.queue_path + '/metadata',
                          self.project_id,
                          body='{"timespace": "Shangri-la"}')

        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Too long
        metadata_size_uplimit = 64

        doc_tmpl = '{{"Dragon Torc":"{0}"}}'
        doc_tmpl_ws = '{{ "Dragon Torc" : "{0}" }}'  # with whitespace
        envelop_length = len(doc_tmpl.format(''))

        for tmpl in doc_tmpl, doc_tmpl_ws:
            gen = '0' * (metadata_size_uplimit - envelop_length + 1)
            doc = tmpl.format(gen)
            self.simulate_put(self.queue_path + '/metadata',
                              self.project_id,
                              body=doc)

            self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_message_deserialization(self):
        # Normal case
        self.simulate_post(self.queue_path + '/messages',
                           self.project_id,
                           body='[{"body": "Dragon Knights", "ttl": 100}]',
                           headers=self.headers)

        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        # Both messages' size are too long
        message_size_uplimit = 256

        obj = {'a': 0, 'b': ''}
        envelop_length = len(json.dumps(obj, separators=(',', ':')))
        obj['b'] = 'x' * (message_size_uplimit - envelop_length + 1)

        for long_body in ('a' * (message_size_uplimit - 2 + 1), obj):
            doc = json.dumps([{'body': long_body, 'ttl': 100}])
            self.simulate_post(self.queue_path + '/messages',
                               self.project_id,
                               body=doc,
                               headers=self.headers)

            self.assertEqual(self.srmock.status, falcon.HTTP_400)

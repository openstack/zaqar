# Copyright 2016 Catalyst IT Ltd.
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

import falcon

from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from zaqar.tests.unit.transport.wsgi import base


class TestPurge(base.V2Base):

    config_file = 'wsgi_mongodb.conf'

    def setUp(self):
        super(TestPurge, self).setUp()

        self.headers = {
            'Client-ID': uuidutils.generate_uuid()
        }
        self.queue_path = self.url_prefix + '/queues/myqueue'
        self.messages_path = self.queue_path + '/messages'
        self.subscription_path = (self.queue_path + '/subscriptions')

        self.messages = {'messages': [{'body': 'A', 'ttl': 300},
                                      {'body': 'B', 'ttl': 400},
                                      {'body': 'C', 'ttl': 500}]}
        self.subscriptions = {"subscriber": "http://ping.me", "ttl": 3600,
                              "options": {"key": "value"}}

    def tearDown(self):
        self.simulate_delete(self.queue_path, headers=self.headers)
        super(TestPurge, self).tearDown()

    def _get_msg_id(self, headers):
        return self._get_msg_ids(headers)[0]

    def _get_msg_ids(self, headers):
        return headers['location'].rsplit('=', 1)[-1].split(',')

    def test_purge_particular_resource(self):
        # Post messages
        messages_body = jsonutils.dumps(self.messages)
        self.simulate_post(self.messages_path, body=messages_body,
                           headers=self.headers)

        msg_ids = self._get_msg_ids(self.srmock.headers_dict)
        for msg_id in msg_ids:
            target = self.messages_path + '/' + msg_id
            self.simulate_get(target, headers=self.headers)
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Post subscriptions
        sub_resp = self.simulate_post(self.subscription_path,
                                      body=jsonutils.dumps(self.subscriptions),
                                      headers=self.headers)

        # Purge queue
        purge_body = jsonutils.dumps({'resource_types': ['messages']})
        self.simulate_post(self.queue_path+"/purge", body=purge_body)

        for msg_id in msg_ids:
            target = self.messages_path + '/' + msg_id
            self.simulate_get(target, headers=self.headers)
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Check subscriptions are still there
        resp_list = self.simulate_get(self.subscription_path,
                                      headers=self.headers)
        resp_list_doc = jsonutils.loads(resp_list[0])
        sid = resp_list_doc['subscriptions'][0]['id']
        sub_resp_doc = jsonutils.loads(sub_resp[0])
        self.assertEqual(sub_resp_doc['subscription_id'], sid)

    def test_purge_by_default(self):
        # Post messages
        messages_body = jsonutils.dumps(self.messages)
        self.simulate_post(self.messages_path, body=messages_body,
                           headers=self.headers)

        msg_ids = self._get_msg_ids(self.srmock.headers_dict)
        for msg_id in msg_ids:
            target = self.messages_path + '/' + msg_id
            self.simulate_get(target, headers=self.headers)
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Post subscriptions
        sub_resp = self.simulate_post(self.subscription_path,
                                      body=jsonutils.dumps(self.subscriptions),
                                      headers=self.headers)

        # Purge queue
        purge_body = jsonutils.dumps({'resource_types': ['messages',
                                                         'subscriptions']})
        self.simulate_post(self.queue_path+"/purge", body=purge_body)

        for msg_id in msg_ids:
            target = self.messages_path + '/' + msg_id
            self.simulate_get(target, headers=self.headers)
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Check subscriptions are still there
        sub_id = jsonutils.loads(sub_resp[0])['subscription_id']
        self.simulate_get(self.subscription_path + "/" + sub_id,
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

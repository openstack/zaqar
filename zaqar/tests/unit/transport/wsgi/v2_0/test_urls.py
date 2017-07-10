# Copyright 2015 Red Hat, Inc.
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

import datetime

import falcon
from oslo_serialization import jsonutils
from oslo_utils import timeutils

from zaqar.common import urls
from zaqar.tests.unit.transport.wsgi import base


class TestURL(base.V2Base):

    config_file = 'wsgi_mongodb.conf'

    def setUp(self):
        super(TestURL, self).setUp()

        self.signed_url_prefix = self.url_prefix + '/queues/shared_queue/share'

    def test_url_generation(self):
        timeutils.set_time_override()
        self.addCleanup(timeutils.clear_time_override)

        data = {'methods': ['GET', 'POST']}
        response = self.simulate_post(self.signed_url_prefix,
                                      body=jsonutils.dumps(data))

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        content = jsonutils.loads(response[0])

        expires = timeutils.utcnow(True) + datetime.timedelta(days=1)
        expires_str = expires.strftime(urls._DATE_FORMAT)

        for field in ['signature', 'project', 'methods', 'paths', 'expires']:
            self.assertIn(field, content)

        self.assertEqual(expires_str, content['expires'])
        self.assertEqual(data['methods'], content['methods'])
        self.assertEqual(['/v2/queues/shared_queue/messages'],
                         content['paths'])

    def test_url_paths(self):
        timeutils.set_time_override()
        self.addCleanup(timeutils.clear_time_override)

        data = {'methods': ['GET', 'POST'],
                'paths': ['messages', 'subscriptions']}
        response = self.simulate_post(self.signed_url_prefix,
                                      body=jsonutils.dumps(data))

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        content = jsonutils.loads(response[0])

        self.assertEqual(
            ['/v2/queues/shared_queue/messages',
             '/v2/queues/shared_queue/subscriptions'],
            content['paths'])

    def test_url_bad_request(self):
        self.simulate_post(self.signed_url_prefix, body='not json')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        data = {'dummy': 'meh'}
        self.simulate_post(self.signed_url_prefix, body=jsonutils.dumps(data))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        data = {'expires': 'wrong date format'}
        self.simulate_post(self.signed_url_prefix, body=jsonutils.dumps(data))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        data = {'methods': 'methods not list'}
        self.simulate_post(self.signed_url_prefix, body=jsonutils.dumps(data))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        data = {'paths': ['notallowed']}
        self.simulate_post(self.signed_url_prefix, body=jsonutils.dumps(data))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_url_verification_success(self):
        data = {'methods': ['GET', 'POST']}
        response = self.simulate_post(self.signed_url_prefix,
                                      body=jsonutils.dumps(data))

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        content = jsonutils.loads(response[0])

        headers = {
            'URL-Signature': content['signature'],
            'URL-Expires': content['expires'],
            'URL-Methods': ','.join(content['methods']),
            'URL-Paths': ','.join(content['paths'])
        }
        headers.update(self.headers)

        response = self.simulate_get(content['paths'][0], headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def _get_msg_id(self, headers):
        return self._get_msg_ids(headers)[0]

    def _get_msg_ids(self, headers):
        return headers['location'].rsplit('=', 1)[-1].split(',')

    def test_url_verification_success_with_message_id(self):
        doc = {'messages': [{'body': 239, 'ttl': 300}]}
        body = jsonutils.dumps(doc)
        self.simulate_post(self.url_prefix + '/queues/shared_queue/messages',
                           body=body, headers=self.headers)
        msg_id = self._get_msg_id(self.srmock.headers_dict)
        data = {'methods': ['GET', 'POST']}
        response = self.simulate_post(self.signed_url_prefix,
                                      body=jsonutils.dumps(data))

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        content = jsonutils.loads(response[0])

        headers = {
            'URL-Signature': content['signature'],
            'URL-Expires': content['expires'],
            'URL-Methods': ','.join(content['methods']),
            'URL-Paths': ','.join(content['paths'])
        }
        headers.update(self.headers)

        self.simulate_get(content['paths'][0] + '/' + msg_id,
                          headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_url_verification_bad_request(self):
        path = self.url_prefix + '/queues/shared_queue/messages'
        expires = timeutils.utcnow() + datetime.timedelta(days=1)
        expires_str = expires.strftime(urls._DATE_FORMAT)

        headers = {
            'URL-Signature': 'dummy',
            'URL-Expires': 'not a real date',
            'URL-Methods': 'GET,POST',
            'URL-Paths': '/v2/queues/shared_queue/messages'
        }
        headers.update(self.headers)
        self.simulate_get(path, headers=headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        headers = {
            'URL-Signature': 'dummy',
            'URL-Expires': expires_str,
            'URL-Methods': '',
            'URL-Paths': '/v2/queues/shared_queue/messages'
        }
        headers.update(self.headers)
        self.simulate_get(path, headers=headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        headers = {
            'URL-Signature': 'dummy',
            'URL-Expires': expires_str,
            'URL-Methods': 'nothing here',
            'URL-Paths': '/v2/queues/shared_queue/messages'
        }
        headers.update(self.headers)
        self.simulate_get(path, headers=headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        headers = {
            'URL-Signature': 'dummy',
            'URL-Expires': expires_str,
            'URL-Methods': 'POST,PUT',
            'URL-Paths': '/v2/queues/shared_queue/messages'
        }
        headers.update(self.headers)
        self.simulate_get(path, headers=headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        headers = {
            'URL-Signature': 'wrong signature',
            'URL-Expires': expires_str,
            'URL-Methods': 'GET,POST',
            'URL-Paths': '/v2/queues/shared_queue/messages'
        }
        headers.update(self.headers)
        self.simulate_get(path, headers=headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        headers = {
            'URL-Signature': 'will fail because of the old date',
            'URL-Expires': '2015-01-01T00:00:00',
            'URL-Methods': 'GET,POST',
            'URL-Paths': '/v2/queues/shared_queue/messages'
        }
        headers.update(self.headers)
        self.simulate_get(path, headers=headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_url_verification_bad_with_message_id(self):
        doc = {'messages': [{'body': 239, 'ttl': 300}]}
        body = jsonutils.dumps(doc)
        self.simulate_post(self.url_prefix + '/queues/shared_queue/messages',
                           body=body, headers=self.headers)
        msg_id = self._get_msg_id(self.srmock.headers_dict)
        data = {'methods': ['GET', 'POST']}
        response = self.simulate_post(self.signed_url_prefix,
                                      body=jsonutils.dumps(data))

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        content = jsonutils.loads(response[0])

        headers = {
            'URL-Signature': content['signature'],
            'URL-Expires': content['expires'],
            'URL-Methods': ','.join(content['methods']),
            'URL-Paths': ','.join('/queues/shared_queue/claims')
        }
        headers.update(self.headers)

        self.simulate_get(content['paths'][0] + '/' + msg_id,
                          headers=headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

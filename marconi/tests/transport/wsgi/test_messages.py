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
import os

import falcon
from falcon import testing

from marconi.tests.transport.wsgi import base


class MessagesBaseTest(base.TestBase):

    def setUp(self):
        super(MessagesBaseTest, self).setUp()

        doc = '{"_ttl": 60}'
        env = testing.create_environ('/v1/480924/queues/fizbit',
                                     method='PUT', body=doc)
        self.app(env, self.srmock)

        self.headers = {
            'Client-ID': '30387f00',
        }

    def tearDown(self):
        env = testing.create_environ('/v1/480924/queues/fizbit',
                                     method='DELETE')
        self.app(env, self.srmock)

        super(MessagesBaseTest, self).tearDown()

    def test_post(self):
        doc = """
        [
            {"body": 239, "ttl": 10},
            {"body": {"key": "value"}, "ttl": 20},
            {"body": [1, 3], "ttl": 30}
        ]
        """

        queue_path = '/v1/480924/queues/fizbit'
        messages_path = queue_path + '/messages'
        env = testing.create_environ(messages_path,
                                     method='POST',
                                     body=doc,
                                     headers=self.headers)

        body = self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        msg_ids = self._get_msg_ids(self.srmock.headers_dict)
        print msg_ids
        self.assertEquals(len(msg_ids), 3)

        body = json.loads(body[0])
        expected_resources = [unicode(messages_path + '/' + id)
                              for id in msg_ids]
        self.assertEquals(expected_resources, body['resources'])
        self.assertFalse(body['partial'])

        sample_messages = json.loads(doc)

        self.assertEquals(len(msg_ids), len(sample_messages))

        lookup = dict([(m['ttl'], m['body']) for m in sample_messages])

        # Test GET on the message resource directly
        for msg_id in msg_ids:
            message_uri = messages_path + '/' + msg_id
            env = testing.create_environ(message_uri, method='GET')

            body = self.app(env, self.srmock)[0]
            self.assertEquals(self.srmock.status, falcon.HTTP_200)
            self.assertEquals(self.srmock.headers_dict['Content-Location'],
                              message_uri)

            msg = json.loads(body)
            self.assertEquals(msg['href'], message_uri)
            self.assertEquals(msg['body'], lookup[msg['ttl']])

        # Test bulk GET
        query_string = 'ids=' + ','.join(msg_ids)
        env = testing.create_environ(queue_path, method='GET',
                                     query_string=query_string)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        body = self.app(env, self.srmock)[0]
        document = json.loads(body)
        expected_ttls = set(m['ttl'] for m in sample_messages)
        actual_ttls = set(m['ttl'] for m in document)
        self.assertFalse(expected_ttls - actual_ttls)

    def test_post_to_mia_queue(self):
        self._post_messages('/v1/480924/queues/nonexistent/messages')
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_post_bad_message(self):
        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method='POST',
                                     headers=self.headers)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method='POST',
                                     body='[',
                                     headers=self.headers)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method='POST',
                                     body='[]',
                                     headers=self.headers)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method='POST',
                                     body='{}',
                                     headers=self.headers)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_delete(self):
        self._post_messages('/v1/480924/queues/fizbit/messages')

        # NOTE(kgriffs): This implictly tests that posting a single
        # message returns a message resource, not a queue resource.
        msg_id = self._get_msg_id(self.srmock.headers_dict)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages/'
                                     + msg_id, method='GET')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages/'
                                     + msg_id, method='DELETE')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages/'
                                     + msg_id, method='GET')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_list(self):
        self._post_messages('/v1/480924/queues/fizbit/messages', repeat=10)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     query_string='limit=3&echo=true',
                                     headers=self.headers)

        body = self.app(env, self.srmock)
        self.assertEquals(self.srmock.headers_dict['Content-Location'],
                          env['PATH_INFO'] + '?' + env['QUERY_STRING'])

        cnt = 0
        while self.srmock.status == falcon.HTTP_200:
            contents = json.loads(body[0])
            [target, params] = contents['links'][0]['href'].split('?')

            for msg in contents['messages']:
                env = testing.create_environ(msg['href'])
                self.app(env, self.srmock)
                self.assertEquals(self.srmock.status, falcon.HTTP_200)

            env = testing.create_environ(target,
                                         query_string=params,
                                         headers=self.headers)
            body = self.app(env, self.srmock)
            cnt += 1

        self.assertEquals(cnt, 4)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Stats
        env = testing.create_environ('/v1/480924/queues/fizbit/stats')

        body = self.app(env, self.srmock)
        countof = json.loads(body[0])

        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        self.assertEquals(self.srmock.headers_dict['Content-Location'],
                          env['PATH_INFO'])
        self.assertEquals(countof['messages']['free'], 10)

        env = testing.create_environ('/v1/480924/queues/nonexistent/messages',
                                     headers=self.headers)

        body = self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_list_with_bad_marker(self):
        self._post_messages('/v1/480924/queues/fizbit/messages', repeat=5)
        query_string = 'limit=3&echo=true&marker=sfhlsfdjh2048'
        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     query_string=query_string,
                                     headers=self.headers)

        self.app(env, self.srmock)
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_no_uuid(self):
        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method='POST',
                                     body='[{"body": 0, "ttl": 0}]')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method='GET')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def _post_messages(self, target, repeat=1):
        doc = json.dumps([{'body': 239, 'ttl': 30}] * repeat)

        env = testing.create_environ(target,
                                     method='POST',
                                     body=doc,
                                     headers=self.headers)
        self.app(env, self.srmock)

    def _get_msg_id(self, headers):
        return headers['Location'].rsplit('/', 1)[-1]

    def _get_msg_ids(self, headers):
        return headers['Location'].rsplit('=', 1)[-1].split(',')


class MessagesSQLiteTests(MessagesBaseTest):

    config_filename = 'wsgi_sqlite.conf'


class MessagesMongoDBTests(MessagesBaseTest):

    config_filename = 'wsgi_mongodb.conf'

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance running')

        super(MessagesMongoDBTests, self).setUp()


class MessagesFaultyDriverTests(base.TestBaseFaulty):

    config_filename = 'wsgi_faulty.conf'

    def test_simple(self):
        doc = '[{"body": 239, "ttl": 10}]'
        headers = {
            'Client-ID': '30387f00',
        }

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method='POST',
                                     body=doc,
                                     headers=headers)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method='GET',
                                     headers=headers)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages'
                                     '/nonexistent',
                                     method='GET')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages'
                                     '/nonexistent',
                                     method='DELETE')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

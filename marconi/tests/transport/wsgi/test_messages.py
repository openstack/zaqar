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
from falcon import testing

import marconi
from marconi.tests import util


class TestMessages(util.TestBase):

    def setUp(self):
        super(TestMessages, self).setUp()

        conf_file = self.conf_path('wsgi_sqlite.conf')
        boot = marconi.Bootstrap(conf_file)

        self.app = boot.transport.app
        self.srmock = testing.StartResponseMock()

        doc = '{ "_ttl": 60 }'
        env = testing.create_environ('/v1/480924/queues/fizbit',
                                     method="PUT", body=doc)
        self.app(env, self.srmock)

        self.headers = {
            'Client-ID': '30387f00',
        }

    def test_post(self):
        doc = '''
        [
            {"body": 239, "ttl": 10},
            {"body": {"key": "value"}, "ttl": 20},
            {"body": [1, 3], "ttl": 30}
        ]
        '''
        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method="POST",
                                     body=doc,
                                     headers=self.headers)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        msg_ids = self._get_msg_ids(self.srmock.headers_dict)
        real_msgs = json.loads(doc)

        self.assertEquals(len(msg_ids), len(real_msgs))

        lookup = dict([(m['ttl'], m['body']) for m in real_msgs])

        for msg_id in msg_ids:
            env = testing.create_environ('/v1/480924/queues/fizbit/messages/'
                                         + msg_id, method="GET")

            body = self.app(env, self.srmock)
            self.assertEquals(self.srmock.status, falcon.HTTP_200)

            msg = json.loads(body[0])
            self.assertEquals(msg['body'], lookup[msg['ttl']])

        self._post_messages('/v1/480924/queues/nonexistent/messages')
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_post_bad_message(self):
        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method="POST",
                                     headers=self.headers)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method="POST",
                                     body='[',
                                     headers=self.headers)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method="POST",
                                     body='[]',
                                     headers=self.headers)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_delete(self):
        self._post_messages('/v1/480924/queues/fizbit/messages')
        [msg_id] = self._get_msg_ids(self.srmock.headers_dict)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages/'
                                     + msg_id, method="GET")

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages/'
                                     + msg_id, method="DELETE")

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages/'
                                     + msg_id, method="GET")

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_list(self):
        self._post_messages('/v1/480924/queues/fizbit/messages', repeat=10)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     query_string='limit=3&echo=true',
                                     headers=self.headers)

        body = self.app(env, self.srmock)

        cnt = 0
        while self.srmock.status == falcon.HTTP_200:
            [target, params] = json.loads(
                body[0])['links'][0]['href'].split('?')
            env = testing.create_environ(target,
                                         query_string=params,
                                         headers=self.headers)
            body = self.app(env, self.srmock)
            cnt += 1

        self.assertEquals(cnt, 4)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        env = testing.create_environ('/v1/480924/queues/nonexistent/messages',
                                     headers=self.headers)

        body = self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_no_uuid(self):
        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method="POST",
                                     body='[{"body": 0, "ttl": 0}]')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method="GET")

        body = self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def tearDown(self):
        env = testing.create_environ('/v1/480924/queues/fizbit',
                                     method="DELETE")
        self.app(env, self.srmock)

        super(TestMessages, self).tearDown()

    def _post_messages(self, target, repeat=1):
        doc = json.dumps([{"body": 239, "ttl": 30}] * repeat)

        env = testing.create_environ(target,
                                     method="POST",
                                     body=doc,
                                     headers=self.headers)
        self.app(env, self.srmock)

    def _get_msg_ids(self, headers_dict):
        return headers_dict['Location'].rsplit('/', 1)[-1].split(',')

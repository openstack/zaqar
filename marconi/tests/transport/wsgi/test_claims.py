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

import pymongo

import falcon
from falcon import testing

from marconi.common import config
from marconi.tests.transport.wsgi import base


class ClaimsBaseTest(base.TestBase):

    def setUp(self):
        super(ClaimsBaseTest, self).setUp()

        doc = '{"_ttl": 60 }'
        env = testing.create_environ('/v1/480924/queues/fizbit',
                                     method='PUT', body=doc)
        self.app(env, self.srmock)

        doc = json.dumps([{'body': 239, 'ttl': 30}] * 10)

        env = testing.create_environ('/v1/480924/queues/fizbit/messages',
                                     method='POST',
                                     body=doc,
                                     headers={'Client-ID': '30387f00'})
        self.app(env, self.srmock)

    def test_bad_claim(self):
        env = testing.create_environ('/v1/480924/queues/fizbit/claims',
                                     method='POST')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ('/v1/480924/queues/fizbit/claims',
                                     method='POST', body='[')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ('/v1/480924/queues/fizbit/claims',
                                     method='POST', body='{}')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_bad_patch(self):
        env = testing.create_environ('/v1/480924/queues/fizbit/claims',
                                     method='POST',
                                     body='{"ttl": 10}')
        self.app(env, self.srmock)
        target = self.srmock.headers_dict['Location']

        env = testing.create_environ(target, method='PATCH')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ(target, method='PATCH', body='{')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_lifecycle(self):
        doc = '{"ttl": 10}'

        # claim some messages

        env = testing.create_environ('/v1/480924/queues/fizbit/claims',
                                     method='POST',
                                     body=doc)

        body = self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

        st = json.loads(body[0])
        target = self.srmock.headers_dict['Location']
        [msg_target, params] = st[0]['href'].split('?')

        # no more messages to claim

        env = testing.create_environ('/v1/480924/queues/fizbit/claims',
                                     method='POST',
                                     body=doc,
                                     query_string='limit=3')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # check its metadata

        env = testing.create_environ(target, method='GET')

        body = self.app(env, self.srmock)
        st = json.loads(body[0])

        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        self.assertEquals(self.srmock.headers_dict['Content-Location'],
                          env['PATH_INFO'])

        self.assertEquals(st['ttl'], 10)

        # delete a message with its associated claim

        env = testing.create_environ(msg_target, query_string=params,
                                     method='DELETE')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        env = testing.create_environ(msg_target, query_string=params)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

        # update the claim

        env = testing.create_environ(target,
                                     body='{"ttl": 60}',
                                     method='PATCH')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # get the claimed messages again

        env = testing.create_environ(target, method='GET')

        body = self.app(env, self.srmock)
        st = json.loads(body[0])
        [msg_target, params] = st['messages'][0]['href'].split('?')

        self.assertEquals(st['ttl'], 60)

        # delete the claim

        env = testing.create_environ(st['href'], method='DELETE')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # can not delete a message with a non-existing claim

        env = testing.create_environ(msg_target, query_string=params,
                                     method='DELETE')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_403)

        env = testing.create_environ(msg_target, query_string=params)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

        # get & update a non existing claim

        env = testing.create_environ(st['href'], method='GET')

        body = self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

        env = testing.create_environ(st['href'], method='PATCH', body=doc)

        body = self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_nonexistent(self):
        doc = '{"ttl": 10}'
        env = testing.create_environ('/v1/480924/queues/nonexistent/claims',
                                     method='POST', body=doc)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def tearDown(self):
        env = testing.create_environ('/v1/480924/queues/fizbit',
                                     method='DELETE')
        self.app(env, self.srmock)

        super(ClaimsBaseTest, self).tearDown()


class ClaimsMongoDBTests(ClaimsBaseTest):

    config_filename = 'wsgi_mongodb.conf'

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance running')
        super(ClaimsMongoDBTests, self).setUp()

        self.cfg = config.namespace('drivers:storage:mongodb').from_options()

    def tearDown(self):
        conn = pymongo.MongoClient(self.cfg.uri)
        conn.drop_database(self.cfg.database)
        super(ClaimsMongoDBTests, self).tearDown()


class ClaimsSQLiteTests(ClaimsBaseTest):

    config_filename = 'wsgi_sqlite.conf'


class ClaimsFaultyDriverTests(base.TestBaseFaulty):

    config_filename = 'wsgi_faulty.conf'

    def test_simple(self):
        doc = '{"ttl": 100}'
        env = testing.create_environ('/v1/480924/queues/fizbit/claims',
                                     method='POST',
                                     body=doc)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        env = testing.create_environ('/v1/480924/queues/fizbit/claims'
                                     '/nonexistent',
                                     method='GET')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        env = testing.create_environ('/v1/480924/queues/fizbit/claims'
                                     '/nonexistent',
                                     method='PATCH',
                                     body=doc)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        env = testing.create_environ('/v1/480924/queues/fizbit/claims'
                                     '/nonexistent',
                                     method='DELETE')

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os

import falcon
from falcon import testing
import pymongo

from marconi.common import config
from marconi.tests.transport.wsgi import base
from marconi import transport


class QueueLifecycleBaseTest(base.TestBase):

    config_filename = None

    def test_simple(self):
        doc = '{"messages": {"ttl": 600}}'
        env = testing.create_environ('/v1/480924/queues/gumshoe',
                                     method="PUT", body=doc)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        location = ('Location', '/v1/480924/queues/gumshoe')
        self.assertIn(location, self.srmock.headers)

        env = testing.create_environ('/v1/480924/queues/gumshoe')
        result = self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        self.assertEquals(result, [doc])

    def test_no_metadata(self):
        env = testing.create_environ('/v1/480924/queues/fizbat', method="PUT")

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_bad_metadata(self):
        env = testing.create_environ('/v1/480924/queues/fizbat',
                                     body="{",
                                     method="PUT")

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        env = testing.create_environ('/v1/480924/queues/fizbat',
                                     body="[]",
                                     method="PUT")

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_too_much_metadata(self):
        doc = '{"messages": {"ttl": 600}, "padding": "%s"}'
        padding_len = transport.MAX_QUEUE_METADATA_SIZE - (len(doc) - 2) + 1
        doc = doc % ('x' * padding_len)
        env = testing.create_environ('/v1/480924/queues/fizbat',
                                     method="PUT", body=doc)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_way_too_much_metadata(self):
        doc = '{"messages": {"ttl": 600}, "padding": "%s"}'
        padding_len = transport.MAX_QUEUE_METADATA_SIZE * 100
        doc = doc % ('x' * padding_len)
        env = testing.create_environ('/v1/480924/queues/gumshoe',
                                     method="PUT", body=doc)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_custom_metadata(self):
        # Set
        doc = '{"messages": {"ttl": 600}, "padding": "%s"}'
        padding_len = transport.MAX_QUEUE_METADATA_SIZE - (len(doc) - 2)
        doc = doc % ('x' * padding_len)
        env = testing.create_environ('/v1/480924/queues/gumshoe',
                                     method="PUT", body=doc)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        # Get
        env = testing.create_environ('/v1/480924/queues/gumshoe')
        result = self.app(env, self.srmock)
        result_doc = json.loads(result[0])
        self.assertEquals(result_doc, json.loads(doc))

    def test_update_metadata(self):
        # Create
        doc1 = '{"messages": {"ttl": 600}}'
        env = testing.create_environ('/v1/480924/queues/xyz',
                                     method="PUT", body=doc1)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        # Update
        doc2 = '{"messages": {"ttl": 100}}'
        env = testing.create_environ('/v1/480924/queues/xyz',
                                     method="PUT", body=doc2)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Get
        env = testing.create_environ('/v1/480924/queues/xyz')
        result = self.app(env, self.srmock)
        result_doc = json.loads(result[0])

        self.assertEquals(result_doc, json.loads(doc2))
        self.assertEquals(self.srmock.headers_dict['Content-Location'],
                          env['PATH_INFO'])


class QueueLifecycleMongoDBTests(QueueLifecycleBaseTest):

    config_filename = 'wsgi_mongodb.conf'

    def setUp(self):
        if not os.environ.get("MONGODB_TEST_LIVE"):
            self.skipTest("No MongoDB instance running")
        super(QueueLifecycleMongoDBTests, self).setUp()

        self.cfg = config.namespace("drivers:storage:mongodb").from_options()

    def tearDown(self):
        conn = pymongo.MongoClient(self.cfg.uri)
        conn.drop_database(self.cfg.database)
        super(QueueLifecycleMongoDBTests, self).tearDown()


class QueueLifecycleSQLiteTests(QueueLifecycleBaseTest):

    config_filename = 'wsgi_sqlite.conf'


class QueueFaultyDriverTests(base.TestBase):

    config_filename = 'wsgi_faulty.conf'

    def test_simple(self):
        doc = '{"messages": {"ttl": 600}}'
        env = testing.create_environ('/v1/480924/queues/gumshoe',
                                     method="PUT", body=doc)

        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        location = ('Location', '/v1/480924/queues/gumshoe')
        self.assertNotIn(location, self.srmock.headers)

        env = testing.create_environ('/v1/480924/queues/gumshoe')
        result = self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)
        self.assertNotEquals(result, [doc])

    def test_bad_document(self):
        env = testing.create_environ('/v1/480924/queues/bad-doc')
        self.app(env, self.srmock)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

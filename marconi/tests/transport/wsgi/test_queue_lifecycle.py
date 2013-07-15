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
import pymongo

from marconi.common import config
from marconi.tests.transport.wsgi import base
from marconi import transport


class QueueLifecycleBaseTest(base.TestBase):

    config_filename = None

    def test_simple(self):
        path = '/v1/queues/gumshoe'

        for project_id in ('480924', 'foo', '', None):
            # Stats
            self.simulate_get(path + '/stats', project_id)
            self.assertEquals(self.srmock.status, falcon.HTTP_404)

            # Create
            doc = '{"messages": {"ttl": 600}}'
            self.simulate_put(path, project_id, body=doc)
            self.assertEquals(self.srmock.status, falcon.HTTP_201)

            location = ('Location', '/v1/queues/gumshoe')
            self.assertIn(location, self.srmock.headers)

            result = self.simulate_get(path, project_id)
            result_doc = json.loads(result[0])
            self.assertEquals(self.srmock.status, falcon.HTTP_200)
            self.assertEquals(result_doc, json.loads(doc))

            # Delete
            self.simulate_delete(path, project_id)
            self.assertEquals(self.srmock.status, falcon.HTTP_204)

            # Get non-existing
            self.simulate_get(path, project_id)
            self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_no_metadata(self):
        self.simulate_put('/v1/queues/fizbat')
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_bad_metadata(self):
        for document in ('{', '[]', '.', '  ', ''):
            self.simulate_put('/v1/queues/fizbat', '7e55e1a7e',
                              body=document)
            self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_too_much_metadata(self):
        doc = '{"messages": {"ttl": 600}, "padding": "%s"}'
        padding_len = transport.MAX_QUEUE_METADATA_SIZE - (len(doc) - 2) + 1
        doc = doc % ('x' * padding_len)

        self.simulate_put('/v1/queues/fizbat', 'deadbeef', body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_way_too_much_metadata(self):
        doc = '{"messages": {"ttl": 600}, "padding": "%s"}'
        padding_len = transport.MAX_QUEUE_METADATA_SIZE * 100
        doc = doc % ('x' * padding_len)

        self.simulate_put('/v1/queues/fizbat', 'deadbeef', body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_custom_metadata(self):
        # Set
        doc = '{"messages": {"ttl": 600}, "padding": "%s"}'
        padding_len = transport.MAX_QUEUE_METADATA_SIZE - (len(doc) - 2)
        doc = doc % ('x' * padding_len)
        self.simulate_put('/v1/queues/fizbat', '480924', body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        # Get
        result = self.simulate_get('/v1/queues/fizbat', '480924')
        result_doc = json.loads(result[0])
        self.assertEquals(result_doc, json.loads(doc))

    def test_update_metadata(self):
        path = '/v1/queues/xyz'
        project_id = '480924'

        # Create
        doc1 = '{"messages": {"ttl": 600}}'
        self.simulate_put(path, project_id, body=doc1)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        # Update
        doc2 = '{"messages": {"ttl": 100}}'
        self.simulate_put(path, project_id, body=doc2)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Get
        result = self.simulate_get(path, project_id)
        result_doc = json.loads(result[0])

        self.assertEquals(result_doc, json.loads(doc2))
        self.assertEquals(self.srmock.headers_dict['Content-Location'],
                          path)

    def test_list(self):
        project_id = '644079696574693'
        alt_project_id = '644079696574694'

        # List empty
        self.simulate_get('/v1/queues', project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Create some
        self.simulate_put('/v1/queues/q1', project_id, body='{"_ttl": 30 }')
        self.simulate_put('/v1/queues/q2', project_id, body='{}')
        self.simulate_put('/v1/queues/q3', project_id, body='{"_ttl": 30 }')

        # List (no metadata)
        result = self.simulate_get('/v1/queues', project_id,
                                   query_string='limit=2')

        result_doc = json.loads(result[0])
        [target, params] = result_doc['links'][0]['href'].split('?')

        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        self.assertEquals(self.srmock.headers_dict['Content-Location'],
                          '/v1/queues?limit=2')

        for queue in result_doc['queues']:
            self.simulate_get(queue['href'], project_id)
            self.assertEquals(self.srmock.status, falcon.HTTP_200)

            self.simulate_get(queue['href'], alt_project_id)
            self.assertEquals(self.srmock.status, falcon.HTTP_404)

            self.assertNotIn('metadata', queue)

        # List with metadata
        result = self.simulate_get('/v1/queues', project_id,
                                   query_string=params + '&detailed=true')

        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        result_doc = json.loads(result[0])
        [target, params] = result_doc['links'][0]['href'].split('?')

        [queue] = result_doc['queues']
        result = self.simulate_get(queue['href'], project_id)
        result_doc = json.loads(result[0])
        self.assertEquals(result_doc, queue['metadata'])

        # List tail
        self.simulate_get(target, project_id, query_string=params)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)


class QueueLifecycleMongoDBTests(QueueLifecycleBaseTest):

    config_filename = 'wsgi_mongodb.conf'

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance running')
        super(QueueLifecycleMongoDBTests, self).setUp()

        self.cfg = config.namespace('drivers:storage:mongodb').from_options()

    def tearDown(self):
        conn = pymongo.MongoClient(self.cfg.uri)
        conn.drop_database(self.cfg.database)
        super(QueueLifecycleMongoDBTests, self).tearDown()


class QueueLifecycleSQLiteTests(QueueLifecycleBaseTest):

    config_filename = 'wsgi_sqlite.conf'


class QueueFaultyDriverTests(base.TestBaseFaulty):

    config_filename = 'wsgi_faulty.conf'

    def test_simple(self):
        path = '/v1/queues/gumshoe'
        doc = '{"messages": {"ttl": 600}}'
        self.simulate_put(path, '480924', body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        location = ('Location', path)
        self.assertNotIn(location, self.srmock.headers)

        result = self.simulate_get(path, '480924')
        result_doc = json.loads(result[0])
        self.assertEquals(self.srmock.status, falcon.HTTP_503)
        self.assertNotEquals(result_doc, json.loads(doc))

        self.simulate_get(path + '/stats', '480924')
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        self.simulate_get('/v1/queues', '480924')
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        self.simulate_delete(path, '480924')
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

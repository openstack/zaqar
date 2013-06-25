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

from marconi.common import config
from marconi.tests.transport.wsgi import base


class ClaimsBaseTest(base.TestBase):

    def setUp(self):
        super(ClaimsBaseTest, self).setUp()

        self.project_id = '480924'
        self.queue_path = '/v1/queues/fizbit'
        self.claims_path = self.queue_path + '/claims'

        doc = '{"_ttl": 60}'

        self.simulate_put(self.queue_path, self.project_id, body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        doc = json.dumps([{'body': 239, 'ttl': 30}] * 10)
        self.simulate_post(self.queue_path + '/messages', self.project_id,
                           body=doc, headers={'Client-ID': '30387f00'})
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

    def tearDown(self):
        self.simulate_delete(self.queue_path, self.project_id)

        super(ClaimsBaseTest, self).tearDown()

    def test_bad_claim(self):
        for doc in (None, '[', '[]', '{}', '.', '"fail"'):
            self.simulate_post(self.claims_path, self.project_id,
                               body=doc)
            self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_bad_patch(self):
        self.simulate_post(self.claims_path, self.project_id,
                           body='{"ttl": 10, "grace": 30}')
        href = self.srmock.headers_dict['Location']

        for doc in (None, '[', '"crunchy"'):
            self.simulate_patch(href, self.project_id, body=doc)
            self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_lifecycle(self):
        doc = '{"ttl": 10, "grace": 30}'

        # First, claim some messages
        body = self.simulate_post(self.claims_path, self.project_id, body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

        claimed = json.loads(body[0])
        claim_href = self.srmock.headers_dict['Location']
        message_href, params = claimed[0]['href'].split('?')

        # No more messages to claim
        self.simulate_post(self.claims_path, self.project_id, body=doc,
                           query_string='limit=3')
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Check the claim's metadata
        body = self.simulate_get(claim_href, self.project_id)
        claim = json.loads(body[0])

        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        self.assertEquals(self.srmock.headers_dict['Content-Location'],
                          claim_href)
        self.assertEquals(claim['ttl'], 10)

        # Delete the message and its associated claim
        self.simulate_delete(message_href, self.project_id,
                             query_string=params)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Try to get it from the wrong project
        self.simulate_get(message_href, 'bogus_project', query_string=params)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

        # Get the message
        self.simulate_get(message_href, self.project_id, query_string=params)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

        # Update the claim
        new_claim = '{"ttl": 60, "grace": 60}'
        self.simulate_patch(claim_href, self.project_id, body=new_claim)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Get the claimed messages (again)
        body = self.simulate_get(claim_href, self.project_id)
        claim = json.loads(body[0])
        message_href, params = claim['messages'][0]['href'].split('?')

        self.assertEquals(claim['ttl'], 60)

        # Delete the claim
        self.simulate_delete(claim['href'], 'bad_id')
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        self.simulate_delete(claim['href'], self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Try to delete a message with an invalid claim ID
        self.simulate_delete(message_href, self.project_id,
                             query_string=params)
        self.assertEquals(self.srmock.status, falcon.HTTP_403)

        # Make sure it wasn't deleted!
        self.simulate_get(message_href, self.project_id, query_string=params)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

        # Try to get a claim that doesn't exist
        self.simulate_get(claim['href'])
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

        # Try to update a claim that doesn't exist
        self.simulate_patch(claim['href'], body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_nonexistent(self):
        self.simulate_post('/v1/queues/nonexistent/claims', self.project_id,
                           body='{"ttl": 10, "grace": 30}')
        self.assertEquals(self.srmock.status, falcon.HTTP_404)


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
        project_id = '480924'
        claims_path = '/v1/queues/fizbit/claims'
        doc = '{"ttl": 100, "grace": 30}'

        self.simulate_post(claims_path, project_id, body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        self.simulate_get(claims_path + '/nichts', project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        self.simulate_patch(claims_path, project_id, body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_405)

        self.simulate_delete(claims_path + '/foo', project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

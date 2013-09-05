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

import ddt
import falcon

from marconi.common import config
from marconi.openstack.common import timeutils
from marconi.tests.transport.wsgi import base


@ddt.ddt
class ClaimsBaseTest(base.TestBase):

    def setUp(self):
        super(ClaimsBaseTest, self).setUp()

        self.wsgi_cfg = config.namespace(
            'drivers:transport:wsgi').from_options()

        self.project_id = '480924'
        self.queue_path = '/v1/queues/fizbit'
        self.claims_path = self.queue_path + '/claims'
        self.messages_path = self.queue_path + '/messages'

        doc = '{"_ttl": 60}'

        self.simulate_put(self.queue_path, self.project_id, body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        doc = json.dumps([{'body': 239, 'ttl': 300}] * 10)
        self.simulate_post(self.queue_path + '/messages', self.project_id,
                           body=doc, headers={'Client-ID': '30387f00'})
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

    def tearDown(self):
        self.simulate_delete(self.queue_path, self.project_id)

        super(ClaimsBaseTest, self).tearDown()

    @ddt.data(None, '[', '[]', '{}', '.', '"fail"')
    def test_bad_claim(self, doc):
        self.simulate_post(self.claims_path, self.project_id, body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        href = self._get_a_claim()

        self.simulate_patch(href, self.project_id, body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_exceeded_claim(self):
        self.simulate_post(self.claims_path, self.project_id,
                           body='{"ttl": 100, "grace": 60}',
                           query_string='limit=21')

        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    @ddt.data((-1, -1), (59, 60), (60, 59), (60, 43201), (43201, 60))
    def test_unacceptable_ttl_or_grace(self, (ttl, grace)):
        self.simulate_post(self.claims_path, self.project_id,
                           body=json.dumps({'ttl': ttl, 'grace': grace}))

        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 59, 43201)
    def test_unacceptable_new_ttl(self, ttl):
        href = self._get_a_claim()

        self.simulate_patch(href, self.project_id,
                            body=json.dumps({'ttl': ttl}))

        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def _get_a_claim(self):
        doc = '{"ttl": 100, "grace": 60}'
        self.simulate_post(self.claims_path, self.project_id, body=doc)
        return self.srmock.headers_dict['Location']

    def test_too_much_metadata(self):
        doc = '{"ttl": 100, "grace": 60}'
        long_doc = doc + (' ' *
                          (self.wsgi_cfg.metadata_max_length - len(doc) + 1))

        self.simulate_post(self.claims_path, self.project_id, body=long_doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        self.simulate_post(self.claims_path, self.project_id, body=doc)
        href = self.srmock.headers_dict['Location']

        self.simulate_patch(href, self.project_id, body=long_doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_lifecycle(self):
        doc = '{"ttl": 100, "grace": 60}'

        # First, claim some messages
        body = self.simulate_post(self.claims_path, self.project_id, body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        claimed = json.loads(body[0])
        claim_href = self.srmock.headers_dict['Location']
        message_href, params = claimed[0]['href'].split('?')

        # No more messages to claim
        self.simulate_post(self.claims_path, self.project_id, body=doc,
                           query_string='limit=3')
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Listing messages, by default, won't include claimed
        body = self.simulate_get(self.messages_path, self.project_id,
                                 headers={'Client-ID': 'foo'})
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Include claimed messages this time
        body = self.simulate_get(self.messages_path, self.project_id,
                                 query_string='include_claimed=true',
                                 headers={'Client-ID': 'foo'})
        listed = json.loads(body[0])
        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        self.assertEquals(len(listed['messages']), len(claimed))

        # Check the claim's metadata
        body = self.simulate_get(claim_href, self.project_id)
        claim = json.loads(body[0])

        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        self.assertEquals(self.srmock.headers_dict['Content-Location'],
                          claim_href)
        self.assertEquals(claim['ttl'], 100)

        # Try to delete the message without submitting a claim_id
        self.simulate_delete(message_href, self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_403)

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
        new_claim_ttl = '{"ttl": 60}'
        creation = timeutils.utcnow()
        self.simulate_patch(claim_href, self.project_id, body=new_claim_ttl)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Get the claimed messages (again)
        body = self.simulate_get(claim_href, self.project_id)
        query = timeutils.utcnow()
        claim = json.loads(body[0])
        message_href, params = claim['messages'][0]['href'].split('?')

        self.assertEquals(claim['ttl'], 60)
        estimated_age = timeutils.delta_seconds(creation, query)
        self.assertTrue(estimated_age > claim['age'])

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
                           body='{"ttl": 100, "grace": 60}')
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

    # NOTE(cpp-cabrera): regression test against bug #1203842
    def test_get_nonexistent_claim_404s(self):
        self.simulate_get(self.claims_path + '/a')
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_delete_nonexistent_claim_204s(self):
        self.simulate_delete(self.claims_path + '/a')
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

    def test_patch_nonexistent_claim_404s(self):
        patch_data = json.dumps({'ttl': 100})
        self.simulate_patch(self.claims_path + '/a', body=patch_data)
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
        doc = '{"ttl": 100, "grace": 60}'

        self.simulate_post(claims_path, project_id, body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        self.simulate_get(claims_path + '/nichts', project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        self.simulate_patch(claims_path + '/nichts', project_id, body=doc)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        self.simulate_delete(claims_path + '/foo', project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

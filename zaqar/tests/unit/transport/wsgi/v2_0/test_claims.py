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

import datetime
import json

import ddt
import falcon
import mock
from oslo_serialization import jsonutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from testtools import matchers

from zaqar import tests as testing
from zaqar.tests.unit.transport.wsgi import base


@ddt.ddt
class TestClaimsMongoDB(base.V2Base):

    config_file = 'wsgi_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestClaimsMongoDB, self).setUp()

        self.default_claim_ttl = self.boot.transport._defaults.claim_ttl
        self.project_id = '737_abc8332832'
        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': self.project_id
        }
        self.queue_path = self.url_prefix + '/queues/fizbit'
        self.claims_path = self.queue_path + '/claims'
        self.messages_path = self.queue_path + '/messages'

        doc = json.dumps({"_ttl": 60})

        self.simulate_put(self.queue_path, body=doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        doc = json.dumps({'messages': [{'body': 239, 'ttl': 300}] * 10})
        self.simulate_post(self.queue_path + '/messages',
                           body=doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def tearDown(self):
        storage = self.boot.storage._storage
        control = self.boot.control
        connection = storage.connection

        connection.drop_database(control.queues_database)

        for db in storage.message_databases:
            connection.drop_database(db)

        self.simulate_delete(self.queue_path, headers=self.headers)

        super(TestClaimsMongoDB, self).tearDown()

    @ddt.data('[', '[]', '.', '"fail"')
    def test_bad_claim(self, doc):
        self.simulate_post(self.claims_path, body=doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        href = self._get_a_claim()

        self.simulate_patch(href, body=doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_exceeded_claim(self):
        self.simulate_post(self.claims_path,
                           body='{"ttl": 100, "grace": 60}',
                           query_string='limit=21', headers=self.headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data((-1, -1), (59, 60), (60, 59), (60, 43201), (43201, 60))
    def test_unacceptable_ttl_or_grace(self, ttl_grace):
        ttl, grace = ttl_grace
        self.simulate_post(self.claims_path,
                           body=json.dumps({'ttl': ttl, 'grace': grace}),
                           headers=self.headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data(-1, 59, 43201)
    def test_unacceptable_new_ttl(self, ttl):
        href = self._get_a_claim()

        self.simulate_patch(href,
                            body=json.dumps({'ttl': ttl}),
                            headers=self.headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_default_ttl_and_grace(self):
        self.simulate_post(self.claims_path,
                           body='{}', headers=self.headers)

        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        body = self.simulate_get(self.srmock.headers_dict['location'],
                                 headers=self.headers)

        claim = jsonutils.loads(body[0])
        self.assertEqual(self.default_claim_ttl, claim['ttl'])

    def _get_a_claim(self):
        doc = '{"ttl": 100, "grace": 60}'
        self.simulate_post(self.claims_path, body=doc, headers=self.headers)
        return self.srmock.headers_dict['Location']

    def test_lifecycle(self):
        doc = '{"ttl": 100, "grace": 60}'

        # First, claim some messages
        body = self.simulate_post(self.claims_path, body=doc,
                                  headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        claimed = jsonutils.loads(body[0])['messages']
        claim_href = self.srmock.headers_dict['Location']
        message_href, params = claimed[0]['href'].split('?')

        # No more messages to claim
        self.simulate_post(self.claims_path, body=doc,
                           query_string='limit=3', headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Listing messages, by default, won't include claimed, will echo
        body = self.simulate_get(self.messages_path,
                                 headers=self.headers,
                                 query_string="echo=true")
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self._empty_message_list(body)

        # Listing messages, by default, won't include claimed, won't echo
        body = self.simulate_get(self.messages_path,
                                 headers=self.headers,
                                 query_string="echo=false")
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self._empty_message_list(body)

        # List messages, include_claimed, but don't echo
        body = self.simulate_get(self.messages_path,
                                 query_string='include_claimed=true'
                                              '&echo=false',
                                 headers=self.headers)

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self._empty_message_list(body)

        # List messages with a different client-id and echo=false.
        # Should return some messages
        headers = self.headers.copy()
        headers["Client-ID"] = uuidutils.generate_uuid()
        body = self.simulate_get(self.messages_path,
                                 query_string='include_claimed=true'
                                              '&echo=false',
                                 headers=headers)

        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Include claimed messages this time, and echo
        body = self.simulate_get(self.messages_path,
                                 query_string='include_claimed=true'
                                              '&echo=true',
                                 headers=self.headers)
        listed = jsonutils.loads(body[0])
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(len(claimed), len(listed['messages']))

        now = timeutils.utcnow() + datetime.timedelta(seconds=10)
        timeutils_utcnow = 'oslo_utils.timeutils.utcnow'
        with mock.patch(timeutils_utcnow) as mock_utcnow:
            mock_utcnow.return_value = now
            body = self.simulate_get(claim_href, headers=self.headers)

        claim = jsonutils.loads(body[0])

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(100, claim['ttl'])
        # NOTE(cpp-cabrera): verify that claim age is non-negative
        self.assertThat(claim['age'], matchers.GreaterThan(-1))

        # Try to delete the message without submitting a claim_id
        self.simulate_delete(message_href, headers=self.headers)
        self.assertEqual(falcon.HTTP_403, self.srmock.status)

        # Delete the message and its associated claim
        self.simulate_delete(message_href,
                             query_string=params, headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Try to get it from the wrong project
        headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': 'bogusproject'
        }
        self.simulate_get(message_href, query_string=params, headers=headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Get the message
        self.simulate_get(message_href, query_string=params,
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Update the claim
        new_claim_ttl = '{"ttl": 60, "grace": 60}'
        creation = timeutils.utcnow()
        self.simulate_patch(claim_href, body=new_claim_ttl,
                            headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Get the claimed messages (again)
        body = self.simulate_get(claim_href, headers=self.headers)
        query = timeutils.utcnow()
        claim = jsonutils.loads(body[0])
        message_href, params = claim['messages'][0]['href'].split('?')

        self.assertEqual(60, claim['ttl'])
        estimated_age = timeutils.delta_seconds(creation, query)
        self.assertGreater(estimated_age, claim['age'])

        # Delete the claim
        self.simulate_delete(claim['href'], headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Try to delete a message with an invalid claim ID
        self.simulate_delete(message_href,
                             query_string=params, headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Make sure it wasn't deleted!
        self.simulate_get(message_href, query_string=params,
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Try to get a claim that doesn't exist
        self.simulate_get(claim['href'], headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Try to update a claim that doesn't exist
        self.simulate_patch(claim['href'], body=doc,
                            headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_post_claim_nonexistent_queue(self):
        path = self.url_prefix + '/queues/nonexistent/claims'
        self.simulate_post(path,
                           body='{"ttl": 100, "grace": 60}',
                           headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_get_claim_nonexistent_queue(self):
        path = self.url_prefix + '/queues/nonexistent/claims/aaabbbba'
        self.simulate_get(path, headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    # NOTE(cpp-cabrera): regression test against bug #1203842
    def test_get_nonexistent_claim_404s(self):
        self.simulate_get(self.claims_path + '/a', headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_delete_nonexistent_claim_204s(self):
        self.simulate_delete(self.claims_path + '/a',
                             headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_patch_nonexistent_claim_404s(self):
        patch_data = json.dumps({'ttl': 100})
        self.simulate_patch(self.claims_path + '/a', body=patch_data,
                            headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)


class TestClaimsFaultyDriver(base.V2BaseFaulty):

    config_file = 'wsgi_faulty.conf'

    def test_simple(self):
        self.project_id = '480924abc_'
        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': self.project_id
        }

        claims_path = self.url_prefix + '/queues/fizbit/claims'
        doc = '{"ttl": 100, "grace": 60}'

        self.simulate_post(claims_path, body=doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_get(claims_path + '/nichts', headers=self.headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_patch(claims_path + '/nichts', body=doc,
                            headers=self.headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_delete(claims_path + '/foo', headers=self.headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

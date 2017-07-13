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
class TestClaimsMongoDB(base.V1Base):

    config_file = 'wsgi_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestClaimsMongoDB, self).setUp()

        self.project_id = '480924'
        self.queue_path = self.url_prefix + '/queues/fizbit'
        self.claims_path = self.queue_path + '/claims'
        self.messages_path = self.queue_path + '/messages'

        doc = '{"_ttl": 60}'

        self.simulate_put(self.queue_path, self.project_id, body=doc)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        doc = jsonutils.dumps([{'body': 239, 'ttl': 300}] * 10)
        self.simulate_post(self.queue_path + '/messages', self.project_id,
                           body=doc, headers={'Client-ID':
                                              uuidutils.generate_uuid()})
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def tearDown(self):
        storage = self.boot.storage._storage
        control = self.boot.control
        connection = storage.connection

        connection.drop_database(control.queues_database)

        for db in storage.message_databases:
            connection.drop_database(db)
        self.simulate_delete(self.queue_path, self.project_id)

        super(TestClaimsMongoDB, self).tearDown()

    @ddt.data(None, '[', '[]', '{}', '.', '"fail"')
    def test_bad_claim(self, doc):
        self.simulate_post(self.claims_path, self.project_id, body=doc)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        href = self._get_a_claim()

        self.simulate_patch(href, self.project_id, body=doc)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_exceeded_claim(self):
        self.simulate_post(self.claims_path, self.project_id,
                           body='{"ttl": 100, "grace": 60}',
                           query_string='limit=21')

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data((-1, -1), (59, 60), (60, 59), (60, 43201), (43201, 60))
    def test_unacceptable_ttl_or_grace(self, ttl_grace):
        ttl, grace = ttl_grace
        self.simulate_post(self.claims_path, self.project_id,
                           body=jsonutils.dumps({'ttl': ttl, 'grace': grace}))

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data(-1, 59, 43201)
    def test_unacceptable_new_ttl(self, ttl):
        href = self._get_a_claim()

        self.simulate_patch(href, self.project_id,
                            body=jsonutils.dumps({'ttl': ttl}))

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def _get_a_claim(self):
        doc = '{"ttl": 100, "grace": 60}'
        self.simulate_post(self.claims_path, self.project_id, body=doc)
        return self.srmock.headers_dict['Location']

    def test_lifecycle(self):
        doc = '{"ttl": 100, "grace": 60}'

        # First, claim some messages
        body = self.simulate_post(self.claims_path, self.project_id, body=doc)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        claimed = jsonutils.loads(body[0])
        claim_href = self.srmock.headers_dict['Location']
        message_href, params = claimed[0]['href'].split('?')

        # No more messages to claim
        self.simulate_post(self.claims_path, self.project_id, body=doc,
                           query_string='limit=3')
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        headers = {
            'Client-ID': uuidutils.generate_uuid(),
        }

        # Listing messages, by default, won't include claimed
        body = self.simulate_get(self.messages_path, self.project_id,
                                 headers=headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Include claimed messages this time
        body = self.simulate_get(self.messages_path, self.project_id,
                                 query_string='include_claimed=true',
                                 headers=headers)
        listed = jsonutils.loads(body[0])
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(len(claimed), len(listed['messages']))

        now = timeutils.utcnow() + datetime.timedelta(seconds=10)
        timeutils_utcnow = 'oslo_utils.timeutils.utcnow'
        with mock.patch(timeutils_utcnow) as mock_utcnow:
            mock_utcnow.return_value = now
            body = self.simulate_get(claim_href, self.project_id)

        claim = jsonutils.loads(body[0])

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(claim_href,
                         self.srmock.headers_dict['Content-Location'])
        self.assertEqual(100, claim['ttl'])
        # NOTE(cpp-cabrera): verify that claim age is non-negative
        self.assertThat(claim['age'], matchers.GreaterThan(-1))

        # Try to delete the message without submitting a claim_id
        self.simulate_delete(message_href, self.project_id)
        self.assertEqual(falcon.HTTP_403, self.srmock.status)

        # Delete the message and its associated claim
        self.simulate_delete(message_href, self.project_id,
                             query_string=params)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Try to get it from the wrong project
        self.simulate_get(message_href, 'bogus_project', query_string=params)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Get the message
        self.simulate_get(message_href, self.project_id, query_string=params)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Update the claim
        new_claim_ttl = '{"ttl": 60}'
        creation = timeutils.utcnow()
        self.simulate_patch(claim_href, self.project_id, body=new_claim_ttl)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Get the claimed messages (again)
        body = self.simulate_get(claim_href, self.project_id)
        query = timeutils.utcnow()
        claim = jsonutils.loads(body[0])
        message_href, params = claim['messages'][0]['href'].split('?')

        self.assertEqual(60, claim['ttl'])
        estimated_age = timeutils.delta_seconds(creation, query)
        self.assertGreater(estimated_age, claim['age'])

        # Delete the claim
        self.simulate_delete(claim['href'], 'bad_id')
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.simulate_delete(claim['href'], self.project_id)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Try to delete a message with an invalid claim ID
        self.simulate_delete(message_href, self.project_id,
                             query_string=params)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Make sure it wasn't deleted!
        self.simulate_get(message_href, self.project_id, query_string=params)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Try to get a claim that doesn't exist
        self.simulate_get(claim['href'])
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Try to update a claim that doesn't exist
        self.simulate_patch(claim['href'], body=doc)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_post_claim_nonexistent_queue(self):
        path = self.url_prefix + '/queues/nonexistent/claims'
        self.simulate_post(path, self.project_id,
                           body='{"ttl": 100, "grace": 60}')
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_get_claim_nonexistent_queue(self):
        path = self.url_prefix + '/queues/nonexistent/claims/aaabbbba'
        self.simulate_get(path)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    # NOTE(cpp-cabrera): regression test against bug #1203842
    def test_get_nonexistent_claim_404s(self):
        self.simulate_get(self.claims_path + '/a')
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_delete_nonexistent_claim_204s(self):
        self.simulate_delete(self.claims_path + '/a')
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_patch_nonexistent_claim_404s(self):
        patch_data = jsonutils.dumps({'ttl': 100})
        self.simulate_patch(self.claims_path + '/a', body=patch_data)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)


class TestClaimsFaultyDriver(base.V1BaseFaulty):

    config_file = 'wsgi_faulty.conf'

    def test_simple(self):
        project_id = '480924'
        claims_path = self.url_prefix + '/queues/fizbit/claims'
        doc = '{"ttl": 100, "grace": 60}'

        self.simulate_post(claims_path, project_id, body=doc)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_get(claims_path + '/nichts', project_id)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_patch(claims_path + '/nichts', project_id, body=doc)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_delete(claims_path + '/foo', project_id)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

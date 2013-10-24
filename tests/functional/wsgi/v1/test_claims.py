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

import uuid

import ddt

from marconi.tests.functional import base
from marconi.tests.functional import helpers


@ddt.ddt
class TestClaims(base.FunctionalTestBase):
    """Tests for Claims."""

    server_class = base.MarconiServer

    def setUp(self):
        super(TestClaims, self).setUp()

        self.queue = uuid.uuid1()
        self.queue_url = ("{url}/{version}/queues/{queue}".format(
                          url=self.cfg.marconi.url,
                          version=self.cfg.marconi.version,
                          queue=self.queue))

        self.client.put(self.queue_url)

        self.claim_url = self.queue_url + '/claims'
        self.client.set_base_url(self.claim_url)

        #Post Messages
        url = self.queue_url + '/messages'
        doc = helpers.create_message_body(messagecount=
                                          self.limits.message_paging_uplimit)
        for i in range(25):
            self.client.post(url, data=doc)

    @ddt.data({}, dict(limit=2))
    def test_claim_messages(self, params):
        """Claim messages."""
        message_count = params.get('limit', 10)

        doc = {"ttl": 300, "grace": 100}

        result = self.client.post(params=params, data=doc)
        self.assertEqual(result.status_code, 201)

        actual_message_count = len(result.json())
        self.assertMessageCount(actual_message_count, message_count)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_with_body, response_headers)

    test_claim_messages.tags = ['smoke', 'positive']

    def test_query_claim(self):
        """Query Claim."""
        params = {'limit': 1}
        doc = {"ttl": 300, "grace": 100}

        result = self.client.post(params=params, data=doc)
        location = result.headers['Location']

        url = self.cfg.marconi.url + location

        result = self.client.get(url)
        self.assertEqual(result.status_code, 200)

    test_query_claim.tags = ['smoke', 'positive']

    def test_claim_more_than_allowed(self):
        """Claim more than max allowed per request.

        Marconi allows a maximum of 20 messages per claim.
        """
        params = {"limit": self.limits.message_paging_uplimit + 1}
        doc = {"ttl": 300, "grace": 100}

        result = self.client.post(params=params, data=doc)
        self.assertEqual(result.status_code, 400)

    test_claim_more_than_allowed.tags = ['negative']

    def test_claim_patch(self):
        """Update Claim."""
        #Test Setup - Post Claim
        doc = {"ttl": 300, "grace": 400}

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 201)

        #Patch Claim
        claim_location = result.headers['Location']
        url = self.cfg.marconi.url + claim_location
        doc_updated = {"ttl": 300}

        result = self.client.patch(url, data=doc_updated)
        self.assertEqual(result.status_code, 204)

        #verify that the claim TTL is updated
        result = self.client.get(url)
        new_ttl = result.json()['ttl']
        self.assertEqual(new_ttl, 300)

    test_claim_patch.tags = ['smoke', 'positive']

    def test_delete_claimed_message(self):
        """Delete message belonging to a Claim."""
        #Test Setup - Post claim
        doc = {"ttl": 60, "grace": 60}

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 201)

        #Delete Claimed Messages
        for rst in result.json():
            href = rst['href']
            url = self.cfg.marconi.url + href
            result = self.client.delete(url)
            self.assertEqual(result.status_code, 204)

    test_delete_claimed_message.tags = ['smoke', 'positive']

    def test_claim_release(self):
        """Release Claim."""
        doc = {"ttl": 300, "grace": 100}

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 201)

        #Extract claim location and construct the claim URL.
        location = result.headers['Location']
        url = self.cfg.marconi.url + location

        #Release Claim.
        result = self.client.delete(url)
        self.assertEqual(result.status_code, 204)

    test_claim_release.tags = ['smoke', 'positive']

    @ddt.data(10000000000000000000, -100, 1, 59, 43201, -10000000000000000000)
    def test_claim_invalid_ttl(self, ttl):
        """Post Claim with invalid TTL.

        The request JSON body will have a TTL value
        outside the allowed range.Allowed ttl values is
        60 <= ttl <= 43200.
        """
        doc = {"ttl": ttl, "grace": 100}

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 400)

    test_claim_invalid_ttl.tags = ['negative']

    @ddt.data(10000000000000000000, -100, 1, 59, 43201, -10000000000000000000)
    def test_claim_invalid_grace(self, grace):
        """Post Claim with invalid grace.

        The request JSON body will have a grace value
        outside the allowed range.Allowed grace values is
        60 <= grace <= 43200.
        """
        doc = {"ttl": 100, "grace": grace}

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 400)

    test_claim_invalid_grace.tags = ['negative']

    @ddt.data(0, -100, 30, 10000000000000000000)
    def test_claim_invalid_limit(self, grace):
        """Post Claim with invalid limit.

        The request url will have a limit outside the allowed range.
        Allowed limit values are 0 < limit <= 20(default max).
        """
        doc = {"ttl": 100, "grace": grace}

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 400)

    test_claim_invalid_limit.tags = ['negative']

    @ddt.data(10000000000000000000, -100, 1, 59, 43201, -10000000000000000000)
    def test_patch_claim_invalid_ttl(self, ttl):
        """Patch Claim with invalid TTL.

        The request JSON body will have a TTL value
        outside the allowed range.Allowed ttl values is
        60 <= ttl <= 43200.
        """
        doc = {"ttl": 100, "grace": 100}

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 201)

        #Extract claim location and construct the claim URL.
        location = result.headers['Location']
        url = self.cfg.marconi.url + location

        #Patch Claim.
        doc = {"ttl": ttl}
        result = self.client.patch(url, data=doc)
        self.assertEqual(result.status_code, 400)

    test_patch_claim_invalid_ttl.tags = ['negative']

    def test_query_non_existing_claim(self):
        """Query Non Existing Claim."""
        path = '/non-existing-claim'
        result = self.client.get(path)
        self.assertEqual(result.status_code, 404)

    test_query_non_existing_claim.tags = ['negative']

    def test_patch_non_existing_claim(self):
        """Patch Non Existing Claim."""
        path = '/non-existing-claim'
        doc = {"ttl": 400}
        result = self.client.patch(path, data=doc)
        self.assertEqual(result.status_code, 404)

    test_patch_non_existing_claim.tags = ['negative']

    def test_delete_non_existing_claim(self):
        """Patch Non Existing Claim."""
        path = '/non-existing-claim'
        result = self.client.delete(path)
        self.assertEqual(result.status_code, 204)

    test_delete_non_existing_claim.tags = ['negative']

    def tearDown(self):
        """Delete Queue after Claim Test."""
        super(TestClaims, self).tearDown()
        self.client.delete(self.queue_url)

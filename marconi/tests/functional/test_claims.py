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
from marconi.tests.functional.util import base
from marconi.tests.functional.util import config
from marconi.tests.functional.util import helpers
from marconi.tests.functional.util import http

import ddt
import json
import uuid


@ddt.ddt
class TestClaims(base.FunctionalTestBase):
    """Tests for Claims."""

    @classmethod
    def setUpClass(cls):
        """Create Queue, Post Messages for Claim Tests."""
        cls.cfg = config.Config()
        cls.header = helpers.create_marconi_headers()

        cls.headers_response_with_body = set(['location',
                                              'content-type'])

    def setUp(self):
        super(TestClaims, self).setUp()

        self.queue_url = self.cfg.base_url + '/queues/{}'.format(uuid.uuid1())
        http.put(self.queue_url, self.header)

        self.claim_url = self.queue_url + '/claims'

        #Post Messages
        url = self.queue_url + '/messages'
        doc = helpers.get_message_body(messagecount=
                                       self.cfg.message_paging_uplimit)
        for i in range(25):
            http.post(url, self.header, doc)

    @ddt.data('', '?limit=2')
    def test_claim_messages(self, url_appender):
        """Claim messages."""
        if url_appender:
            message_count = int(url_appender.split('?limit=')[1])
        else:
            message_count = 10

        url = self.claim_url + url_appender
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        actual_message_count = len(result.json())
        self.assertMessageCount(message_count, actual_message_count)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_with_body, response_headers)

    test_claim_messages.tags = ['smoke', 'positive']

    def test_query_claim(self):
        """Query Claim."""
        url = self.claim_url + '?limit=1'
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        location = result.headers['Location']

        url = self.cfg.base_server + location

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

    test_query_claim.tags = ['smoke', 'positive']

    def test_claim_more_than_allowed(self):
        """Claim more than max allowed per request.

        Marconi allows a maximum of 20 messages per claim.
        """
        url = self.claim_url + '?limit=' + \
            str(self.cfg.message_paging_uplimit + 1)
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

    test_claim_more_than_allowed.tags = ['negative']

    def test_claim_patch(self):
        """Update Claim."""
        #Test Setup - Post Claim
        doc = '{"ttl": 300, "grace": 400}'

        result = http.post(self.claim_url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        #Patch Claim
        claim_location = result.headers['Location']
        url = self.cfg.base_server + claim_location
        doc_updated = '{"ttl": 300}'

        result = http.patch(url, self.header, doc_updated)
        self.assertEqual(result.status_code, 204)

        #verify that the claim TTL is updated
        result = http.get(url, self.header)
        new_ttl = result.json()['ttl']
        self.assertEqual(new_ttl, 300)

    test_claim_patch.tags = ['smoke', 'positive']

    def test_delete_claimed_message(self):
        """Delete message belonging to a Claim."""
        #Test Setup - Post claim
        doc = '{"ttl": 60, "grace": 60}'

        result = http.post(self.claim_url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        href_list = [result.json()[i]['href']
                     for i in range(len(result.json()))]
        url_list = [self.cfg.base_server + href
                    for href in href_list]

        #Delete Claimed Messages
        for url in url_list:
            result = http.delete(url, self.header)
            self.assertEqual(result.status_code, 204)

    test_delete_claimed_message.tags = ['smoke', 'positive']

    def test_claim_release(self):
        """Release Claim."""
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(self.claim_url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        #Extract claim location and construct the claim URL.
        location = result.headers['Location']
        url = self.cfg.base_server + location

        #Release Claim.
        result = http.delete(url, self.header)
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

        result = http.post(self.claim_url, self.header, json.dumps(doc))
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

        result = http.post(self.claim_url, self.header, json.dumps(doc))
        self.assertEqual(result.status_code, 400)

    test_claim_invalid_grace.tags = ['negative']

    @ddt.data(0, -100, 30, 10000000000000000000)
    def test_claim_invalid_limit(self, grace):
        """Post Claim with invalid limit.

        The request url will have a limit outside the allowed range.
        Allowed limit values are 0 < limit <= 20(default max).
        """
        doc = {"ttl": 100, "grace": grace}

        result = http.post(self.claim_url, self.header, json.dumps(doc))
        self.assertEqual(result.status_code, 400)

    test_claim_invalid_limit.tags = ['negative']

    @ddt.data(10000000000000000000, -100, 1, 59, 43201, -10000000000000000000)
    def test_patch_claim_invalid_ttl(self, ttl):
        """Patch Claim with invalid TTL.

        The request JSON body will have a TTL value
        outside the allowed range.Allowed ttl values is
        60 <= ttl <= 43200.
        """
        doc = '{"ttl": 100, "grace": 100}'

        result = http.post(self.claim_url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        #Extract claim location and construct the claim URL.
        location = result.headers['Location']
        url = self.cfg.base_server + location

        #Patch Claim.
        doc = {"ttl": ttl}
        result = http.patch(url, self.header, json.dumps(doc))
        self.assertEqual(result.status_code, 400)

    test_patch_claim_invalid_ttl.tags = ['negative']

    def tearDown(self):
        """Delete Queue after Claim Test."""
        super(TestClaims, self).tearDown()
        http.delete(self.queue_url, self.header)

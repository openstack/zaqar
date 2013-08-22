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
from marconi.tests.system.claim import claimfnlib
from marconi.tests.system.common import config
from marconi.tests.system.common import functionlib
from marconi.tests.system.common import http
from marconi.tests.system.messages import msgfnlib

import ddt
import json


@ddt.ddt
class TestClaims(functionlib.TestUtils):
    """Tests for Claims."""

    def setUp(self):
        super(TestClaims, self).setUp()
        self.cfg = config.Config()
        self.header = functionlib.create_marconi_headers()

        self.headers_response_with_body = set(['location',
                                               'content-type'])

    def test_000_claim_setup(self):
        """Create Queue, Post Messages for Claim Tests."""
        url = self.cfg.base_url + '/queues/claimtestqueue'

        result = http.put(url, self.header)
        self.assertEqual(result.status_code, 201)

        #Post Messages
        url = self.cfg.base_url + '/queues/claimtestqueue/messages'
        doc = msgfnlib.get_message_body(messagecount=
                                        self.cfg.message_paging_uplimit)
        for i in range(25):
            result = http.post(url, self.header, doc)
            self.assertEqual(result.status_code, 201)

    test_000_claim_setup.tags = ['smoke', 'positive']

    def test_001_claim_2messages(self):
        """Claim 2 messages."""
        message_count = 2
        url = self.cfg.base_url + '/queues/claimtestqueue/claims?limit=2'
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        test_result_flag = claimfnlib.verify_claim_msg(
            message_count, result.headers, result.text)
        self.assertEqual(test_result_flag, True)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_with_body, response_headers)

    test_001_claim_2messages.tags = ['smoke', 'positive']

    def test_002_claim_default_messages(self):
        """Claim messages with no URL parameters.

        By default, Marconi will return 10 messages.
        """
        default_message_count = 10
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        test_result_flag = claimfnlib.verify_claim_msg(
            default_message_count, result.headers, result.text)
        self.assertEqual(test_result_flag, True)

    test_002_claim_default_messages.tags = ['smoke', 'positive']

    def test_003_claim_more_than_allowed(self):
        """Claim more than max allowed per request.

        Marconi allows a maximum of 20 messages per claim.
        """
        url = self.cfg.base_url + '/queues/claimtestqueue/claims?limit=' +  \
            str(self.cfg.message_paging_uplimit + 1)
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

    test_003_claim_more_than_allowed.tags = ['negative']

    def test_004_claim_patch(self):
        """Update Claim."""
        #Test Setup - Post Claim
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 300, "grace": 400}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        #Patch Claim
        claim_location = result.headers['Location']
        url = self.cfg.base_server + claim_location
        doc_updated = '{"ttl": 300}'

        result = http.patch(url, self.header, doc_updated)
        self.assertEqual(result.status_code, 204)

        test_result_flag = claimfnlib.verify_patch_claim(url,
                                                         self.header, 300)
        self.assertEqual(test_result_flag, True)

    test_004_claim_patch.tags = ['smoke', 'positive']

    def test_005_delete_claimed_message(self):
        """Delete message belonging to a Claim."""
        #Test Setup - Post claim
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 60, "grace": 60}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        #Delete Claimed Message & Verify the delete
        test_result_flag = claimfnlib.delete_claimed_msgs(
            result.headers, result.text)
        self.assertEqual(test_result_flag, True)

    test_005_delete_claimed_message.tags = ['smoke', 'positive']

    def test_006_claim_release(self):
        """Release Claim."""
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        #Extract claim location and construct the claim URL.
        location = result.headers['Location']
        url = self.cfg.base_server + location

        #Release Claim.
        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_006_claim_release.tags = ['smoke', 'positive']

    @ddt.data(10000000000000000000, -100, 1, 59, 43201, -10000000000000000000)
    def test_007_claim_invalid_ttl(self, ttl):
        """Post Claim with invalid TTL.

        The request JSON body will have a TTL value
        outside the allowed range.Allowed ttl values is
        60 <= ttl <= 43200.
        """
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = {"ttl": ttl, "grace": 100}

        result = http.post(url, self.header, json.dumps(doc))
        self.assertEqual(result.status_code, 400)

    test_007_claim_invalid_ttl.tags = ['negative']

    @ddt.data(10000000000000000000, -100, 1, 59, 43201, -10000000000000000000)
    def test_008_claim_invalid_grace(self, grace):
        """Post Claim with invalid grace.

        The request JSON body will have a grace value
        outside the allowed range.Allowed grace values is
        60 <= grace <= 43200.
        """
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = {"ttl": 100, "grace": grace}

        result = http.post(url, self.header, json.dumps(doc))
        self.assertEqual(result.status_code, 400)

    test_008_claim_invalid_grace.tags = ['negative']

    @ddt.data(0, -100, 30, 10000000000000000000)
    def test_009_claim_invalid_limit(self, grace):
        """Post Claim with invalid limit.

        The request url will have a limit outside the allowed range.
        Allowed limit values are 0 < limit <= 20(default max).
        """
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = {"ttl": 100, "grace": grace}

        result = http.post(url, self.header, json.dumps(doc))
        self.assertEqual(result.status_code, 400)

    test_009_claim_invalid_limit.tags = ['negative']

    @ddt.data(10000000000000000000, -100, 1, 59, 43201, -10000000000000000000)
    def test_010_patch_claim_invalid_ttl(self, ttl):
        """Patch Claim with invalid TTL.

        The request JSON body will have a TTL value
        outside the allowed range.Allowed ttl values is
        60 <= ttl <= 43200.
        """
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 100, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        #Extract claim location and construct the claim URL.
        location = result.headers['Location']
        url = self.cfg.base_server + location

        #Patch Claim.
        doc = {"ttl": ttl}
        result = http.patch(url, self.header, json.dumps(doc))
        self.assertEqual(result.status_code, 400)

    test_010_patch_claim_invalid_ttl.tags = ['negative']

    def test_999_claim_teardown(self):
        """Delete Queue after Claim Tests."""
        url = self.cfg.base_url + '/queues/claimtestqueue'

        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_999_claim_teardown.tags = ['smoke', 'positive']

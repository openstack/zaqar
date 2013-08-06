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

import time


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
        doc = msgfnlib.get_message_body(messagecount=50)
        for i in range(5):
            result = http.post(url, self.header, doc)
            self.assertEqual(result.status_code, 201)

    test_000_claim_setup.tags = ['smoke', 'positive']

    def test_001_claim_2messages(self):
        """Claim 2 messages."""
        message_count = 2
        url = self.cfg.base_url + '/queues/claimtestqueue/claims?limit=2'
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 200)

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
        self.assertEqual(result.status_code, 200)

        test_result_flag = claimfnlib.verify_claim_msg(
            default_message_count, result.headers, result.text)
        self.assertEqual(test_result_flag, True)

    test_002_claim_default_messages.tags = ['smoke', 'positive']

    def test_003_claim_15messages(self):
        """Claim 15 messages."""
        message_count = 15
        url = self.cfg.base_url + '/queues/claimtestqueue/claims?limit=15'
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 200)

        test_result_flag = claimfnlib.verify_claim_msg(
            message_count, result.headers, result.text)
        self.assertEqual(test_result_flag, True)

    test_003_claim_15messages.tags = ['positive']

    def test_004_claim_55messages(self):
        """Claim more than max allowed per request.

        Marconi allows a maximum of 50 messages per claim.
        """
        message_count = 55
        url = self.cfg.base_url + '/queues/claimtestqueue/claims?limit=55'
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 200)

        test_result_flag = claimfnlib.verify_claim_msg(
            message_count, result.headers, result.text)
        self.assertEqual(test_result_flag, True)

    test_004_claim_55messages.tags = ['positive']

    def test_005_claim_patch(self):
        """Update Claim."""
        #Test Setup - Post Claim
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 300, "grace": 400}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 200)

        #Patch Claim
        claim_location = result.headers['Location']
        url = self.cfg.base_server + claim_location
        doc_updated = '{"ttl": 300}'

        result = http.patch(url, self.header, doc_updated)
        self.assertEqual(result.status_code, 204)

        test_result_flag = claimfnlib.verify_patch_claim(url,
                                                         self.header, 300)
        self.assertEqual(test_result_flag, True)

    test_005_claim_patch.tags = ['smoke', 'positive']

    def test_006_claim_delete_message(self):
        """Delete message belonging to a Claim."""
        #Test Setup - Post claim
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 60, "grace": 10}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 200)

        #Delete Claimed Message & Verify the delete
        test_result_flag = claimfnlib.delete_claimed_msgs(
            result.headers, result.text)
        self.assertEqual(test_result_flag, True)

    test_006_claim_delete_message.tags = ['smoke', 'positive']

    def test_007_claim_expired(self):
        """Update, Get and Release Expired Claim."""
        #Test Setup - Post Claim.
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 1, "grace": 0}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 200)

        time.sleep(2)

        #Extract claim location and construct the claim URL.
        location = result.headers['Location']
        url = self.cfg.base_server + location

        #Update Expired Claim.
        doc = '{"ttl": 300}'
        result = http.patch(url, self.header, doc)
        self.assertEqual(result.status_code, 404)

        #Get Expired Claim.
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

        #Release Expired Claim.
        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_007_claim_expired.tags = ['smoke', 'positive']

    def test_008_claim_expired_delete_message(self):
        """Get & Delete Message from an Expired Claim."""
        #Test Setup - Post Claim.
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 1, "grace": 0}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 200)

        time.sleep(2)

        #Get Claim & Message Locations.
        claim_location = result.headers['Location']
        message_location = result.json()[0]['href']

        #Delete message with expired claim ID
        url = self.cfg.base_server + message_location
        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 403)

        #Delete Expired Claim.
        url = self.cfg.base_server + claim_location
        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_008_claim_expired_delete_message.tags = ['smoke', 'positive']

    def test_009_claim_release(self):
        """Release Claim."""
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 300, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 200)

        #Extract claim location and construct the claim URL.
        location = result.headers['Location']
        url = self.cfg.base_server + location

        #Release Claim.
        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_009_claim_release.tags = ['smoke', 'positive']

    def test_010_claim_big_int(self):
        """Post Claim with big TTL/ Grace.

        The request JSON body will have an integer
        outside the range -2^63 ~ 2^63-1.
        """
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 10000000000000000000, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 100, "grace": -10000000000000000000}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

    test_010_claim_big_int.tags = ['negative']

    def test_011_claim_negative_int(self):
        """Post Claim with negative TTL/ Grace."""
        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": -100, "grace": 100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

        url = self.cfg.base_url + '/queues/claimtestqueue/claims'
        doc = '{"ttl": 100, "grace": -100}'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

    test_011_claim_negative_int.tags = ['negative']

    def test_999_claim_teardown(self):
        """Delete Queue after Claim Tests."""
        url = self.cfg.base_url + '/queues/claimtestqueue'

        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_999_claim_teardown.tags = ['smoke', 'positive']

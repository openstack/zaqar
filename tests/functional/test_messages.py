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
from marconi.tests.functional import base  # noqa
from marconi.tests.functional import config
from marconi.tests.functional import helpers
from marconi.tests.functional import http

import ddt
import uuid


@ddt.ddt
class TestMessages(base.FunctionalTestBase):

    """Tests for Messages."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = config.Config()
        cls.header = helpers.create_marconi_headers()

        cls.headers_response_with_body = set(['location',
                                              'content-type'])

    def setUp(self):
        super(TestMessages, self).setUp()

        self.queue_url = self.cfg.base_url + '/queues/{}'.format(uuid.uuid1())
        http.put(self.queue_url, self.header)

        self.message_url = self.queue_url + '/messages'

    def test_message_single_insert(self):
        """Insert Single Message into the Queue.

        This test also verifies that claimed messages are
        retuned (or not) depending on the include_claimed flag.
        """
        doc = helpers.get_message_body(messagecount=1)

        result = http.post(self.message_url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_with_body, response_headers)

        # GET on posted message
        href = result.json()['resources'][0]
        url = self.cfg.base_server + href

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        # Compare message metadata
        result_body = result.json()['body']
        posted_metadata = doc[0]['body']
        self.assertEqual(result_body, posted_metadata)

        # Post a claim & verify the include_claimed flag.
        url = self.queue_url + '/claims'
        doc = '{"ttl": 300, "grace": 100}'
        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        url = self.message_url + '?include_claimed=true&echo=true'
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        response_message_body = result.json()["messages"][0]["body"]
        self.assertEqual(response_message_body, posted_metadata)

        # By default, include_claimed = false
        result = http.get(self.message_url, self.header)
        self.assertEqual(result.status_code, 204)

    test_message_single_insert.tags = ['smoke', 'positive']

    def test_message_bulk_insert(self):
        """Bulk Insert Messages into the Queue."""
        message_count = 10
        doc = helpers.get_message_body(messagecount=message_count)

        result = http.post(self.message_url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        # GET on posted messages
        location = result.headers['location']
        url = self.cfg.base_server + location
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        # Compare message metadata
        result_body = [result.json()[i]['body']
                       for i in range(len(result.json()))]
        result_body.sort()

        posted_metadata = [doc[i]['body']
                           for i in range(message_count)]
        posted_metadata.sort()

        self.assertEqual(result_body, posted_metadata)

    test_message_bulk_insert.tags = ['smoke', 'positive']

    @ddt.data('', '&limit=5')
    def test_get_message(self, url_param):
        """Get Messages."""
        if url_param:
            expected_msg_count = int(url_param.split('&limit=')[1])
        else:
            expected_msg_count = 10

        # Test Setup
        doc = helpers.get_message_body(messagecount=20)
        result = http.post(self.message_url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        url = self.message_url + '?echo=True' + url_param

        #Follow the hrefs & perform GET, till the end of messages i.e. http 204
        while result.status_code in [201, 200]:
            result = http.get(url, self.header)
            self.assertIn(result.status_code, [200, 204])

            if result.status_code == 200:
                actual_msg_count = len(result.json()['messages'])
                self.assertMessageCount(actual_msg_count, expected_msg_count)

                href = result.json()['links'][0]['href']
                url = self.cfg.base_server + href

        self.assertEqual(result.status_code, 204)

    test_get_message.tags = ['smoke', 'positive']

    def test_message_delete(self):
        """Delete Message."""
        # Test Setup
        doc = helpers.get_message_body(messagecount=1)
        result = http.post(self.message_url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        # Delete posted message
        href = result.json()['resources'][0]
        url = self.cfg.base_server + href

        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_message_delete.tags = ['smoke', 'positive']

    def test_message_bulk_delete(self):
        """Bulk Delete Messages."""
        doc = helpers.get_message_body(messagecount=10)
        result = http.post(self.message_url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        # Delete posted messages
        location = result.headers['Location']
        url = self.cfg.base_server + location

        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_message_bulk_delete.tags = ['smoke', 'positive']

    def test_message_delete_nonexisting(self):
        """Delete non-existing Messages."""
        url = self.message_url + '/non-existing'
        result = http.delete(url, self.header)

        self.assertEqual(result.status_code, 204)

    test_message_delete_nonexisting.tags = ['negative']

    def test_message_partial_delete(self):
        """Delete Messages will be partially successful."""
        doc = helpers.get_message_body(messagecount=3)
        result = http.post(self.message_url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        # Delete posted message
        location = result.headers['Location']
        url = self.cfg.base_server + location
        url += ',nonexisting'
        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_message_partial_delete.tags = ['negative']

    def test_message_partial_get(self):
        """Get Messages will be partially successful."""
        doc = helpers.get_message_body(messagecount=3)
        result = http.post(self.message_url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        # Get posted message and a nonexisting message
        location = result.headers['Location']
        url = self.cfg.base_server + location
        url += ',nonexisting'
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

    test_message_partial_get.tags = ['negative']

    def test_message_bulk_insert_60(self):
        """Insert more than max allowed messages.

        Marconi allows  a maximum of 50 message per POST.
        """
        doc = helpers.get_message_body(messagecount=60)

        result = http.post(self.message_url, self.header, doc)
        self.assertEqual(result.status_code, 400)

    test_message_bulk_insert_60.tags = ['negative']

    @ddt.data(10000000000000000000, -100, 0, 30, -10000000000000000000)
    def test_message_get_invalid_limit(self, limit):
        """Get Messages with invalid value for limit.

        Allowed values for limit are 0 < limit <= 20(configurable).
        """
        url = self.message_url + '?limit=' + str(limit)
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 400)

    test_message_get_invalid_limit.tags = ['negative']

    def test_message_bulk_delete_negative(self):
        """Delete more messages than allowed in a single request.

        By default, max messages that can be deleted in a single
        request is 20.
        """
        url = self.message_url + '?ids=' \
            + ','.join(str(i) for i in
                       range(self.cfg.message_paging_uplimit + 1))
        result = http.delete(url, self.header)

        self.assertEqual(result.status_code, 400)

    test_message_bulk_delete_negative.tags = ['negative']

    def test_message_bulk_get_negative(self):
        """GET more messages by id than allowed in a single request.

        By default, max messages that can be fetched in a single
        request is 20.
        """
        url = self.message_url + '?ids=' \
            + ','.join(str(i) for i in
                       range(self.cfg.message_paging_uplimit + 1))
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 400)

    test_message_bulk_get_negative.tags = ['negative']

    def test_get_messages_malformed_marker(self):
        """Get messages with non-existing marker."""
        url = self.message_url + '?marker=invalid'

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_get_messages_malformed_marker.tags = ['negative']

    def tearDown(self):
        super(TestMessages, self).tearDown()
        http.delete(self.queue_url, self.header)

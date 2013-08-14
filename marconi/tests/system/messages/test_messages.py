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
from marconi.tests.system.common import config
from marconi.tests.system.common import functionlib
from marconi.tests.system.common import http
from marconi.tests.system.messages import msgfnlib

import ddt


@ddt.ddt
class TestMessages(functionlib.TestUtils):

    """Tests for Messages."""

    def setUp(self):
        super(TestMessages, self).setUp()
        self.cfg = config.Config()
        self.header = functionlib.create_marconi_headers()

        self.headers_response_with_body = set(['location',
                                               'content-type'])

    def test_000_message_setup(self):
        """Create Queue for Message Tests."""
        url = self.cfg.base_url + '/queues/messagetestqueue'
        result = http.put(url, self.header)

        self.assertEqual(result.status_code, 201)

    test_000_message_setup.tags = ['smoke', 'positive']

    def test_001_message_single_insert(self):
        """Insert Single Message into the Queue.

        This test also verifies that claimed messages are
        retuned (or not) depending on the include_claimed flag.
        """
        doc = msgfnlib.get_message_body(messagecount=1)
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_with_body, response_headers)

        #GET on posted message
        href = result.json()['resources'][0]
        url = self.cfg.base_server + href

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        #Compare message metadata
        result_body = result.json()['body']
        posted_metadata = doc[0]['body']
        self.assertEqual(result_body, posted_metadata)

        #Post a claim & verify the include_claimed flag.
        url = self.cfg.base_url + '/queues/messagetestqueue/claims'
        doc = '{"ttl": 300, "grace": 100}'
        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        url = self.cfg.base_url + '/queues/messagetestqueue/messages' \
                                  '?include_claimed=true&echo=true'
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        response_message_body = result.json()["messages"][0]["body"]
        self.assertEqual(response_message_body, posted_metadata)

        #By default, include_claimed = false
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_001_message_single_insert.tags = ['smoke', 'positive']

    def test_002_message_bulk_insert(self):
        """Bulk Insert Messages into the Queue."""
        message_count = 10
        doc = msgfnlib.get_message_body(messagecount=message_count)
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'
        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        #GET on posted messages
        location = result.headers['location']
        url = self.cfg.base_server + location
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        #Compare message metadata
        result_body = [result.json()[i]['body']
                       for i in range(len(result.json()))]
        result_body.sort()

        posted_metadata = [doc[i]['body']
                           for i in range(message_count)]
        posted_metadata.sort()

        self.assertEqual(result_body, posted_metadata)

    test_002_message_bulk_insert.tags = ['smoke', 'positive']

    def test_003_message_get_no_params(self):
        """Get Messages with no params."""
        default_msg_count = 10
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        test_result_flag = msgfnlib.verify_get_msgs(default_msg_count,
                                                    result.headers,
                                                    result.text)
        self.assertEqual(test_result_flag, True)

    test_003_message_get_no_params.tags = ['smoke', 'positive']

    def test_004_message_get_limit_5(self):
        """Get Messages with no params."""
        msg_count = 5
        url = self.cfg.base_url + '/queues/messagetestqueue/messages?limit=5'

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        test_result_flag = msgfnlib.verify_get_msgs(msg_count,
                                                    result.headers,
                                                    result.text)
        self.assertEqual(test_result_flag, True)

    test_004_message_get_limit_5.tags = ['smoke', 'positive']

    def test_005_message_delete(self):
        """Delete Message."""
        doc = msgfnlib.get_message_body(messagecount=1)
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'
        result = http.post(url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        #Delete posted message
        href = result.json()['resources'][0]
        url = self.cfg.base_server + href

        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_005_message_delete.tags = ['smoke', 'positive']

    def test_006_message_bulk_delete(self):
        """Bulk Delete Messages."""
        doc = msgfnlib.get_message_body(messagecount=10)
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'
        result = http.post(url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        #Delete posted messages
        location = result.headers['Location']
        url = self.cfg.base_server + location

        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_006_message_bulk_delete.tags = ['smoke', 'positive']

    def test_007_message_delete_nonexisting(self):
        """Delete non-existing Messages."""
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'   \
                                  '/non-existing'
        result = http.delete(url, self.header)

        self.assertEqual(result.status_code, 204)

    test_007_message_delete_nonexisting.tags = ['negative']

    def test_008_message_partial_delete(self):
        """Delete Messages will be partially successful."""
        doc = msgfnlib.get_message_body(messagecount=3)
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'
        result = http.post(url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        #Delete posted message
        location = result.headers['Location']
        url = self.cfg.base_server + location
        url += ',nonexisting'
        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_008_message_partial_delete.tags = ['negative']

    def test_009_message_partial_get(self):
        """Get Messages will be partially successful."""
        doc = msgfnlib.get_message_body(messagecount=3)
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'
        result = http.post(url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        #Get posted message and a nonexisting message
        location = result.headers['Location']
        url = self.cfg.base_server + location
        url += ',nonexisting'
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

    test_009_message_partial_get.tags = ['negative']

    def test_010_message_bulk_insert_60(self):
        """Insert more than max allowed messages.

        Marconi allows  a maximum of 50 message per POST.
        """
        doc = msgfnlib.get_message_body(messagecount=60)
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'

        result = http.post(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

    test_010_message_bulk_insert_60.tags = ['negative']

    @ddt.data(10000000000000000000, -100, 0, 30, -10000000000000000000)
    def test_011_message_get_invalid_limit(self, limit):
        """Get Messages with invalid value for limit.

        Allowed values for limit are 0 < limit <= 20(configurable).
        """
        url = self.cfg.base_url + '/queues/messagetestqueue/messages?limit=' \
            + str(limit)
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 400)

    test_011_message_get_invalid_limit.tags = ['negative']

    def test_012_message_bulk_delete(self):
        """Delete more messages than allowed in a single request.

        By default, max messages that can be deleted in a single
        request is 20.
        """
        url = self.cfg.base_url + '/queues/messagetestqueue/messages?ids=' \
            + ','.join(str(i) for i in
                       range(self.cfg.message_paging_uplimit + 1))
        result = http.delete(url, self.header)

        self.assertEqual(result.status_code, 400)

    test_012_message_bulk_delete.tags = ['negative']

    def test_013_message_bulk_get(self):
        """GET more messages by id than allowed in a single request.

        By default, max messages that can be fetched in a single
        request is 20.
        """
        url = self.cfg.base_url + '/queues/messagetestqueue/messages?ids=' \
            + ','.join(str(i) for i in
                       range(self.cfg.message_paging_uplimit + 1))
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 400)

    test_013_message_bulk_get.tags = ['negative']

    def test_014_get_messages_malformed_marker(self):
        """Get messages with non-existing marker."""
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'  \
            '?marker=invalid'

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_014_get_messages_malformed_marker.tags = ['negative']

    def test_999_message_teardown(self):
        url = self.cfg.base_url + '/queues/messagetestqueue'
        http.delete(url, self.header)

    test_999_message_teardown.tags = ['smoke', 'positive']

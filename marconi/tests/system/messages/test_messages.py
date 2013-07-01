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

import testtools


class TestMessages(testtools.TestCase):
    """Tests for Messages."""

    def setUp(self):
        super(TestMessages, self).setUp()
        self.cfg = config.Config()
        self.header = functionlib.create_marconi_headers()

    def test_000_message_setup(self):
        """Create Queue for Message Tests."""
        url = self.cfg.base_url + '/queues/messagetestqueue'
        doc = '{"queuemetadata": "message test queue"}'
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 201)

    test_000_message_setup.tags = ['smoke', 'positive']

    def test_001_message_single_insert(self):
        """Insert Single Message into the Queue."""
        doc = msgfnlib.get_message_body(messagecount=1)
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'
        result = http.post(url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        #GET on posted message
        location = result.headers['location']
        url = self.cfg.base_server + location
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        #Compare message metadata
        result_body = result.json()[0]['body']
        posted_metadata = doc[0]['body']
        self.assertEqual(result_body, posted_metadata)

    test_001_message_single_insert.tags = ['smoke', 'positive']

    def test_002_message_bulk_insert(self):
        """Bulk Insert Messages into the Queue."""
        message_count = 30
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
        result_body = [result.json()['messages'][i]['body']
                       for i in range(len(result.json()['messages']))]
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

    def test_005_message_get_echo_false(self):
        """Get Messages with echo=false."""
        url = self.cfg.base_url + \
            '/queues/messagetestqueue/messages?echo=false'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 204)

    test_005_message_get_echo_false.tags = ['smoke', 'positive']

    def test_006_message_delete(self):
        """Delete Message."""
        doc = msgfnlib.get_message_body(messagecount=1)
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'
        result = http.post(url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        #Delete posted message
        location = result.headers['location']
        url = self.cfg.base_server + location
        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_006_message_delete.tags = ['smoke', 'positive']

    def test_007_message_bulk_insert_60(self):
        """Insert more than max allowed messages.

        Marconi allows  a maximum of 50 message per POST.
        """
        doc = msgfnlib.get_message_body(messagecount=60)
        url = self.cfg.base_url + '/queues/messagetestqueue/messages'
        result = http.post(url, self.header, doc)

        self.assertEqual(result.status_code, 400)

    test_007_message_bulk_insert_60.tags = ['negative']

    def test_999_message_teardown(self):
        url = self.cfg.base_url + '/queues/messagetestqueue'
        http.delete(url, self.header)
    test_999_message_teardown.tags = ['smoke', 'positive']

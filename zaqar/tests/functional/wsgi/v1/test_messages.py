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

from __future__ import division

import json
import uuid

import ddt

from zaqar.tests.functional import base
from zaqar.tests.functional import helpers


@ddt.ddt
class TestMessages(base.V1FunctionalTestBase):

    """Tests for Messages."""

    server_class = base.ZaqarServer

    def setUp(self):
        super(TestMessages, self).setUp()

        self.queue = uuid.uuid1()
        self.queue_url = ("{url}/{version}/queues/{queue}".format(
                          url=self.cfg.zaqar.url,
                          version="v1",
                          queue=self.queue))

        self.client.put(self.queue_url)

        self.message_url = self.queue_url + '/messages'
        self.client.set_base_url(self.message_url)

    def tearDown(self):
        self.client.delete(self.queue_url)
        super(TestMessages, self).tearDown()

    def _post_large_bulk_insert(self, offset):
        """Insert just under than max allowed messages."""

        message1 = {"body": '', "ttl": 300}
        message2 = {"body": '', "ttl": 120}

        doc = [message1, message2]
        overhead = len(json.dumps(doc))

        half_size = (self.limits.max_messages_post_size - overhead) // 2
        message1['body'] = helpers.generate_random_string(half_size)
        message2['body'] = helpers.generate_random_string(half_size + offset)

        return self.client.post(data=doc)

    def test_message_single_insert(self):
        """Insert Single Message into the Queue.

        This test also verifies that claimed messages are
        retuned (or not) depending on the include_claimed flag.
        """
        doc = helpers.create_message_body(messagecount=1)

        result = self.client.post(data=doc)
        self.assertEqual(201, result.status_code)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_with_body, response_headers)

        # GET on posted message
        href = result.json()['resources'][0]
        url = self.cfg.zaqar.url + href

        result = self.client.get(url)
        self.assertEqual(200, result.status_code)

        # Compare message metadata
        result_body = result.json()['body']
        posted_metadata = doc[0]['body']
        self.assertEqual(posted_metadata, result_body)

        # Post a claim & verify the include_claimed flag.
        url = self.queue_url + '/claims'
        doc = {"ttl": 300, "grace": 100}
        result = self.client.post(url, data=doc)
        self.assertEqual(201, result.status_code)

        params = {'include_claimed': True,
                  'echo': True}
        result = self.client.get(params=params)
        self.assertEqual(200, result.status_code)

        response_message_body = result.json()["messages"][0]["body"]
        self.assertEqual(posted_metadata, response_message_body)

        # By default, include_claimed = false
        result = self.client.get(self.message_url)
        self.assertEqual(204, result.status_code)

    test_message_single_insert.tags = ['smoke', 'positive']

    def test_message_bulk_insert(self):
        """Bulk Insert Messages into the Queue."""
        message_count = self.limits.max_messages_per_page
        doc = helpers.create_message_body(messagecount=message_count)

        result = self.client.post(data=doc)
        self.assertEqual(201, result.status_code)

        # GET on posted messages
        location = result.headers['location']
        url = self.cfg.zaqar.url + location
        result = self.client.get(url)
        self.assertEqual(200, result.status_code)

        self.skipTest('Bug #1273335 - Get set of messages returns wrong hrefs '
                      '(happens randomly)')

        # Verify that the response json schema matches the expected schema
        self.assertSchema(result.json(), 'message_get_many')

        # Compare message metadata
        result_body = [result.json()[i]['body']
                       for i in range(len(result.json()))]
        result_body.sort()

        posted_metadata = [doc[i]['body']
                           for i in range(message_count)]
        posted_metadata.sort()

        self.assertEqual(posted_metadata, result_body)

    test_message_bulk_insert.tags = ['smoke', 'positive']

    @ddt.data({}, {'limit': 5})
    def test_get_message(self, params):
        """Get Messages."""

        expected_msg_count = params.get('limit', 10)

        # Test Setup
        doc = helpers.create_message_body(
            messagecount=self.limits.max_messages_per_page)

        result = self.client.post(data=doc)
        self.assertEqual(201, result.status_code)

        url = ''
        params['echo'] = True

        # Follow the hrefs & perform GET, till the end of messages i.e. http
        # 204
        while result.status_code in [201, 200]:
            result = self.client.get(url, params=params)
            self.assertIn(result.status_code, [200, 204])

            if result.status_code == 200:
                actual_msg_count = len(result.json()['messages'])
                self.assertMessageCount(actual_msg_count, expected_msg_count)

                self.assertSchema(result.json(), 'message_list')

                href = result.json()['links'][0]['href']
                url = self.cfg.zaqar.url + href

        self.assertEqual(204, result.status_code)

    test_get_message.tags = ['smoke', 'positive']

    def test_message_delete(self):
        """Delete Message."""
        # Test Setup
        doc = helpers.create_message_body(messagecount=1)
        result = self.client.post(data=doc)
        self.assertEqual(201, result.status_code)

        # Delete posted message
        href = result.json()['resources'][0]
        url = self.cfg.zaqar.url + href

        result = self.client.delete(url)
        self.assertEqual(204, result.status_code)

        result = self.client.get(url)
        self.assertEqual(404, result.status_code)

    test_message_delete.tags = ['smoke', 'positive']

    def test_message_bulk_delete(self):
        """Bulk Delete Messages."""
        doc = helpers.create_message_body(messagecount=10)
        result = self.client.post(data=doc)

        self.assertEqual(201, result.status_code)

        # Delete posted messages
        location = result.headers['Location']
        url = self.cfg.zaqar.url + location

        result = self.client.delete(url)
        self.assertEqual(204, result.status_code)

        result = self.client.get(url)
        self.assertEqual(204, result.status_code)

    test_message_bulk_delete.tags = ['smoke', 'positive']

    def test_message_delete_nonexisting(self):
        """Delete non-existing Messages."""
        result = self.client.delete('/non-existing')

        self.assertEqual(204, result.status_code)

    test_message_delete_nonexisting.tags = ['negative']

    def test_message_partial_delete(self):
        """Delete Messages will be partially successful."""
        doc = helpers.create_message_body(messagecount=3)
        result = self.client.post(data=doc)

        self.assertEqual(201, result.status_code)

        # Delete posted message
        location = result.headers['Location']
        url = self.cfg.zaqar.url + location
        url += ',nonexisting'
        result = self.client.delete(url)
        self.assertEqual(204, result.status_code)

    test_message_partial_delete.tags = ['negative']

    def test_message_partial_get(self):
        """Get Messages will be partially successful."""
        doc = helpers.create_message_body(messagecount=3)
        result = self.client.post(data=doc)

        self.assertEqual(201, result.status_code)

        # Get posted message and a nonexisting message
        location = result.headers['Location']
        url = self.cfg.zaqar.url + location
        url += ',nonexisting'
        result = self.client.get(url)
        self.assertEqual(200, result.status_code)

        self.assertSchema(result.json(), "message_get_many")

    test_message_partial_get.tags = ['negative']

    @ddt.data(-10, -1, 0)
    def test_message_bulk_insert_large_bodies(self, offset):
        """Insert just under than max allowed messages."""
        result = self._post_large_bulk_insert(offset)
        self.assertEqual(201, result.status_code)

    test_message_bulk_insert_large_bodies.tags = ['positive']

    @ddt.data(1, 10)
    def test_message_bulk_insert_large_bodies_(self, offset):
        """Insert just under than max allowed messages."""
        result = self._post_large_bulk_insert(offset)
        self.assertEqual(400, result.status_code)

    test_message_bulk_insert_large_bodies_.tags = ['negative']

    def test_message_bulk_insert_oversized(self):
        """Insert more than max allowed size."""

        doc = '[{{"body": "{0}", "ttl": 300}}, {{"body": "{1}", "ttl": 120}}]'
        overhead = len(doc.format('', ''))

        half_size = (self.limits.max_messages_post_size - overhead) // 2
        doc = doc.format(helpers.generate_random_string(half_size),
                         helpers.generate_random_string(half_size + 1))

        result = self.client.post(data=doc)
        self.assertEqual(400, result.status_code)

    test_message_bulk_insert_oversized.tags = ['negative']

    @ddt.data(10000000000000000000, -100, 0, 30, -10000000000000000000)
    def test_message_get_invalid_limit(self, limit):
        """Get Messages with invalid value for limit.

        Allowed values for limit are 0 < limit <= 20(configurable).
        """
        params = {'limit': limit}
        result = self.client.get(params=params)
        self.assertEqual(400, result.status_code)

    test_message_get_invalid_limit.tags = ['negative']

    def test_message_bulk_delete_negative(self):
        """Delete more messages than allowed in a single request.

        By default, max messages that can be deleted in a single
        request is 20.
        """
        url = (self.message_url + '?ids=' +
               ','.join(str(i) for i in
                        range(self.limits.max_messages_per_page + 1)))
        result = self.client.delete(url)

        self.assertEqual(400, result.status_code)

    test_message_bulk_delete_negative.tags = ['negative']

    def test_message_bulk_get_negative(self):
        """GET more messages by id than allowed in a single request.

        By default, max messages that can be fetched in a single
        request is 20.
        """
        url = (self.message_url + '?ids=' +
               ','.join(str(i) for i in
                        range(self.limits.max_messages_per_page + 1)))
        result = self.client.get(url)

        self.assertEqual(400, result.status_code)

    test_message_bulk_get_negative.tags = ['negative']

    def test_get_messages_malformed_marker(self):
        """Get messages with non-existing marker."""
        url = self.message_url + '?marker=invalid'

        result = self.client.get(url)
        self.assertEqual(204, result.status_code)

    test_get_messages_malformed_marker.tags = ['negative']

    @ddt.data(None, '1234', 'aa2-bb3',
              '103e09c6-31b7-11e3-86bc-b8ca3ad0f5d81',
              '103e09c6-31b7-11e3-86bc-b8ca3ad0f5d')
    def test_get_messages_invalid_client_id(self, client_id):
        """Get messages with invalid client id."""
        url = self.message_url

        header = helpers.create_zaqar_headers(self.cfg)
        header['Client-ID'] = client_id

        result = self.client.get(url, headers=header)
        self.assertEqual(400, result.status_code)

    test_get_messages_invalid_client_id.tags = ['negative']

    def test_query_non_existing_message(self):
        """Get Non Existing Message."""
        path = '/non-existing-message'
        result = self.client.get(path)
        self.assertEqual(404, result.status_code)

    test_query_non_existing_message.tags = ['negative']

    def test_query_non_existing_message_set(self):
        """Get Set of Non Existing Messages."""
        path = '?ids=not_there1,not_there2'
        result = self.client.get(path)
        self.assertEqual(204, result.status_code)

    test_query_non_existing_message_set.tags = ['negative']

    def test_delete_non_existing_message(self):
        """Delete Non Existing Message."""
        path = '/non-existing-message'
        result = self.client.delete(path)
        self.assertEqual(204, result.status_code)

    test_delete_non_existing_message.tags = ['negative']

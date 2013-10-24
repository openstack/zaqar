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

from marconi.tests.functional import base  # noqa
from marconi.tests.functional import helpers


@ddt.ddt
class TestMessages(base.FunctionalTestBase):
    """Tests for Messages."""

    server_class = base.MarconiServer

    def setUp(self):
        super(TestMessages, self).setUp()

        self.queue = uuid.uuid1()
        self.queue_url = ("{url}/{version}/queues/{queue}".format(
                          url=self.cfg.marconi.url,
                          version=self.cfg.marconi.version,
                          queue=self.queue))

        self.client.put(self.queue_url)

        self.message_url = self.queue_url + '/messages'
        self.client.set_base_url(self.message_url)

    def test_message_single_insert(self):
        """Insert Single Message into the Queue.

        This test also verifies that claimed messages are
        retuned (or not) depending on the include_claimed flag.
        """
        doc = helpers.create_message_body(messagecount=1)

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 201)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_with_body, response_headers)

        # GET on posted message
        href = result.json()['resources'][0]
        url = self.cfg.marconi.url + href

        result = self.client.get(url)
        self.assertEqual(result.status_code, 200)

        # Compare message metadata
        result_body = result.json()['body']
        posted_metadata = doc[0]['body']
        self.assertEqual(result_body, posted_metadata)

        # Post a claim & verify the include_claimed flag.
        url = self.queue_url + '/claims'
        doc = {"ttl": 300, "grace": 100}
        result = self.client.post(url, data=doc)
        self.assertEqual(result.status_code, 201)

        params = {'include_claimed': True,
                  'echo': True}
        result = self.client.get(params=params)
        self.assertEqual(result.status_code, 200)

        response_message_body = result.json()["messages"][0]["body"]
        self.assertEqual(response_message_body, posted_metadata)

        # By default, include_claimed = false
        result = self.client.get(self.message_url)
        self.assertEqual(result.status_code, 204)

    test_message_single_insert.tags = ['smoke', 'positive']

    def test_message_bulk_insert(self):
        """Bulk Insert Messages into the Queue."""
        message_count = self.limits.message_paging_uplimit
        doc = helpers.create_message_body(messagecount=message_count)

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 201)

        # GET on posted messages
        location = result.headers['location']
        url = self.cfg.marconi.url + location
        result = self.client.get(url)
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

    @ddt.data({}, {'limit': 5})
    def test_get_message(self, params):
        """Get Messages."""

        expected_msg_count = params.get('limit', 10)

        # Test Setup
        doc = helpers.create_message_body(messagecount=
                                          self.limits.message_paging_uplimit)
        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 201)

        url = ''
        params['echo'] = True

        #Follow the hrefs & perform GET, till the end of messages i.e. http 204
        while result.status_code in [201, 200]:
            result = self.client.get(url, params=params)
            self.assertIn(result.status_code, [200, 204])

            if result.status_code == 200:
                actual_msg_count = len(result.json()['messages'])
                self.assertMessageCount(actual_msg_count, expected_msg_count)

                href = result.json()['links'][0]['href']
                url = self.cfg.marconi.url + href

        self.assertEqual(result.status_code, 204)

    test_get_message.tags = ['smoke', 'positive']

    def test_message_delete(self):
        """Delete Message."""
        # Test Setup
        doc = helpers.create_message_body(messagecount=1)
        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 201)

        # Delete posted message
        href = result.json()['resources'][0]
        url = self.cfg.marconi.url + href

        result = self.client.delete(url)
        self.assertEqual(result.status_code, 204)

        result = self.client.get(url)
        self.assertEqual(result.status_code, 404)

    test_message_delete.tags = ['smoke', 'positive']

    def test_message_bulk_delete(self):
        """Bulk Delete Messages."""
        doc = helpers.create_message_body(messagecount=10)
        result = self.client.post(data=doc)

        self.assertEqual(result.status_code, 201)

        # Delete posted messages
        location = result.headers['Location']
        url = self.cfg.marconi.url + location

        result = self.client.delete(url)
        self.assertEqual(result.status_code, 204)

        result = self.client.get(url)
        self.assertEqual(result.status_code, 204)

    test_message_bulk_delete.tags = ['smoke', 'positive']

    def test_message_delete_nonexisting(self):
        """Delete non-existing Messages."""
        result = self.client.delete('/non-existing')

        self.assertEqual(result.status_code, 204)

    test_message_delete_nonexisting.tags = ['negative']

    def test_message_partial_delete(self):
        """Delete Messages will be partially successful."""
        doc = helpers.create_message_body(messagecount=3)
        result = self.client.post(data=doc)

        self.assertEqual(result.status_code, 201)

        # Delete posted message
        location = result.headers['Location']
        url = self.cfg.marconi.url + location
        url += ',nonexisting'
        result = self.client.delete(url)
        self.assertEqual(result.status_code, 204)

    test_message_partial_delete.tags = ['negative']

    def test_message_partial_get(self):
        """Get Messages will be partially successful."""
        doc = helpers.create_message_body(messagecount=3)
        result = self.client.post(data=doc)

        self.assertEqual(result.status_code, 201)

        # Get posted message and a nonexisting message
        location = result.headers['Location']
        url = self.cfg.marconi.url + location
        url += ',nonexisting'
        result = self.client.get(url)
        self.assertEqual(result.status_code, 200)

    test_message_partial_get.tags = ['negative']

    def test_message_bulk_insert_60(self):
        """Insert more than max allowed messages.

        Marconi allows  a maximum of 50 message per POST.
        """
        doc = helpers.create_message_body(messagecount=60)

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 400)

    test_message_bulk_insert_60.tags = ['negative']

    @ddt.data(10000000000000000000, -100, 0, 30, -10000000000000000000)
    def test_message_get_invalid_limit(self, limit):
        """Get Messages with invalid value for limit.

        Allowed values for limit are 0 < limit <= 20(configurable).
        """
        params = {'limit': limit}
        result = self.client.get(params=params)
        self.assertEqual(result.status_code, 400)

    test_message_get_invalid_limit.tags = ['negative']

    def test_message_bulk_delete_negative(self):
        """Delete more messages than allowed in a single request.

        By default, max messages that can be deleted in a single
        request is 20.
        """
        url = self.message_url + '?ids=' \
            + ','.join(str(i) for i in
                       range(self.limits.message_paging_uplimit + 1))
        result = self.client.delete(url)

        self.assertEqual(result.status_code, 400)

    test_message_bulk_delete_negative.tags = ['negative']

    def test_message_bulk_get_negative(self):
        """GET more messages by id than allowed in a single request.

        By default, max messages that can be fetched in a single
        request is 20.
        """
        url = self.message_url + '?ids=' \
            + ','.join(str(i) for i in
                       range(self.limits.message_paging_uplimit + 1))
        result = self.client.get(url)

        self.assertEqual(result.status_code, 400)

    test_message_bulk_get_negative.tags = ['negative']

    def test_get_messages_malformed_marker(self):
        """Get messages with non-existing marker."""
        url = self.message_url + '?marker=invalid'

        result = self.client.get(url)
        self.assertEqual(result.status_code, 204)

    test_get_messages_malformed_marker.tags = ['negative']

    @ddt.data(None, '1234', 'aa2-bb3',
              '103e09c6-31b7-11e3-86bc-b8ca3ad0f5d81',
              '103e09c6-31b7-11e3-86bc-b8ca3ad0f5d')
    def test_get_messages_invalid_client_id(self, client_id):
        """Get messages with invalid client id."""
        url = self.message_url

        header = helpers.create_marconi_headers(self.cfg)
        header['Client-ID'] = client_id

        result = self.client.get(url, headers=header)
        self.assertEqual(result.status_code, 400)

    test_get_messages_invalid_client_id.tags = ['negative']

    def test_query_non_existing_message(self):
        """Get Non Existing Message."""
        path = '/non-existing-message'
        result = self.client.get(path)
        self.assertEqual(result.status_code, 404)

    test_query_non_existing_message.tags = ['negative']

    def test_query_non_existing_message_set(self):
        """Get Set of Non Existing Messages."""
        path = '?ids=not_there1,not_there2'
        result = self.client.get(path)
        self.assertEqual(result.status_code, 204)

    test_query_non_existing_message_set.tags = ['negative']

    def test_delete_non_existing_message(self):
        """Delete Non Existing Message."""
        path = '/non-existing-message'
        result = self.client.delete(path)
        self.assertEqual(result.status_code, 204)

    test_delete_non_existing_message.tags = ['negative']

    def tearDown(self):
        super(TestMessages, self).tearDown()
        self.client.delete(self.queue_url)

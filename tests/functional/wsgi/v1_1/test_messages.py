# Copyright (c) 2014 Rackspace, Inc.
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

import uuid

import ddt

from marconi.tests.functional import base
from marconi.tests.functional import helpers


@ddt.ddt
class TestMessages(base.V1_1FunctionalTestBase):

    """Message Tests Specific to V1.1."""

    server_class = base.MarconiServer

    def setUp(self):
        super(TestMessages, self).setUp()

        self.queue = uuid.uuid1()  # Generate a random queue ID
        self.queue_url = ("{url}/{version}/queues/{queue}".format(
            url=self.cfg.marconi.url,
            version="v1.1",
            queue=self.queue))

        self.headers = helpers.create_marconi_headers(self.cfg)
        self.client.headers = self.headers

        self.client.put(self.queue_url)  # Create the queue
        self.message_url = self.queue_url + '/messages'
        self.client.set_base_url(self.message_url)

    def tearDown(self):
        self.client.delete(self.queue_url)  # Remove the queue
        super(TestMessages, self).tearDown()

    def _post_large_bulk_insert(self, offset):
        """Insert just under than max allowed messages."""

        doc = '[{{"body": "{0}", "ttl": 300}}, {{"body": "{1}", "ttl": 120}}]'
        overhead = len(doc.format('', ''))

        half_size = (self.limits.max_message_size - overhead) // 2
        doc = doc.format(helpers.generate_random_string(half_size),
                         helpers.generate_random_string(half_size + offset))

        return self.client.post(data=doc)

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
        self.assertEqual(result.status_code, 200)

    test_message_single_insert.tags = ['smoke', 'positive']

    def test_message_bulk_insert(self):
        """Bulk Insert Messages into the Queue."""
        message_count = self.limits.max_messages_per_page
        doc = helpers.create_message_body(messagecount=message_count)

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 201)

        # GET on posted messages
        location = result.headers['location']
        url = self.cfg.marconi.url + location
        result = self.client.get(url)
        self.assertEqual(result.status_code, 200)

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

        self.assertEqual(result_body, posted_metadata)

    test_message_bulk_insert.tags = ['smoke', 'positive']

    @ddt.data({}, {'limit': 5})
    def test_get_message(self, params):
        """Get Messages."""

        # Note(abettadapur): This will now return 200s and [].
        # Needs to be addressed when feature patch goes in
        self.skipTest("Not supported")
        expected_msg_count = params.get('limit',
                                        self.limits.max_messages_per_page)

        # Test Setup
        doc = helpers.create_message_body(
            messagecount=self.limits.max_messages_per_page)

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 201)

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
        self.assertEqual(result.status_code, 404)

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

    @ddt.data(5, 1)
    def test_messages_pop(self, limit=5):
        """Pop messages from a queue."""
        doc = helpers.create_message_body(messagecount=limit)
        result = self.client.post(data=doc)

        self.assertEqual(result.status_code, 201)

        # Pop messages
        url = self.message_url + '?pop=' + str(limit)

        result = self.client.delete(url)
        self.assertEqual(result.status_code, 200)

        params = {'echo': True}

        result = self.client.get(self.message_url, params=params)
        self.assertEqual(result.status_code, 200)

        messages = result.json()['messages']
        self.assertEqual(messages, [])

    test_messages_pop.tags = ['smoke', 'positive']

    @ddt.data(10000000, 0, -1)
    def test_messages_pop_invalid(self, limit):
        """Pop messages from a queue."""
        doc = helpers.create_message_body(
            messagecount=self.limits.max_messages_per_page)
        result = self.client.post(data=doc)

        self.assertEqual(result.status_code, 201)

        # Pop messages
        url = self.message_url + '?pop=' + str(limit)

        result = self.client.delete(url)
        self.assertEqual(result.status_code, 400)

        params = {'echo': True}
        result = self.client.get(self.message_url, params=params)
        self.assertEqual(result.status_code, 200)

        messages = result.json()['messages']
        self.assertNotEqual(messages, [])

    test_messages_pop_invalid.tags = ['smoke', 'negative']

    def test_messages_delete_pop_and_id(self):
        """Delete messages with pop & id params in the request."""
        doc = helpers.create_message_body(
            messagecount=1)
        result = self.client.post(data=doc)

        self.assertEqual(result.status_code, 201)
        location = result.headers['Location']

        # Pop messages
        url = self.cfg.marconi.url + location + '&pop=1'

        result = self.client.delete(url)
        self.assertEqual(result.status_code, 400)

        params = {'echo': True}

        result = self.client.get(self.message_url, params=params)
        self.assertEqual(result.status_code, 200)

        messages = result.json()['messages']
        self.assertNotEqual(messages, [])

    test_messages_delete_pop_and_id.tags = ['smoke', 'negative']

    def test_messages_pop_empty_queue(self):
        """Pop messages from an empty queue."""
        url = self.message_url + '?pop=2'

        result = self.client.delete(url)
        self.assertEqual(result.status_code, 200)

        messages = result.json()['messages']
        self.assertEqual(messages, [])

    test_messages_pop_empty_queue.tags = ['smoke', 'positive']

    def test_messages_pop_one(self):
        """Pop single messages from a queue."""
        doc = helpers.create_message_body(
            messagecount=self.limits.max_messages_per_page)
        result = self.client.post(data=doc)

        self.assertEqual(result.status_code, 201)

        # Pop Single Message
        url = self.message_url + '?pop=1'

        result = self.client.delete(url)
        self.assertEqual(result.status_code, 200)

        # Get messages from the queue & verify message count
        params = {'echo': True, 'limit': self.limits.max_messages_per_page}

        result = self.client.get(self.message_url, params=params)
        self.assertEqual(result.status_code, 200)

        expected_msg_count = self.limits.max_messages_per_page - 1
        actual_msg_count = len(result.json()['messages'])
        self.assertEqual(expected_msg_count, actual_msg_count)

    test_messages_pop_one.tags = ['smoke', 'positive']

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

    @ddt.data(-10, -1, 0)
    def test_message_bulk_insert_large_bodies(self, offset):
        """Insert just under than max allowed messages."""
        result = self._post_large_bulk_insert(offset)
        self.assertEqual(result.status_code, 201)

    test_message_bulk_insert_large_bodies.tags = ['positive']

    @ddt.data(1, 10)
    def test_message_bulk_insert_large_bodies_(self, offset):
        """Insert just under than max allowed messages."""
        result = self._post_large_bulk_insert(offset)
        self.assertEqual(result.status_code, 400)

    test_message_bulk_insert_large_bodies_.tags = ['negative']

    def test_message_bulk_insert_oversized(self):
        """Insert more than max allowed size."""

        doc = '[{{"body": "{0}", "ttl": 300}}, {{"body": "{1}", "ttl": 120}}]'
        overhead = len(doc.format('', ''))

        half_size = (self.limits.max_message_size - overhead) // 2
        doc = doc.format(helpers.generate_random_string(half_size),
                         helpers.generate_random_string(half_size + 1))

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 400)

    test_message_bulk_insert_oversized.tags = ['negative']

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
        url = (self.message_url + '?ids='
               + ','.join(str(i) for i in
                          range(self.limits.max_messages_per_page + 1)))
        result = self.client.delete(url)

        self.assertEqual(result.status_code, 400)

    test_message_bulk_delete_negative.tags = ['negative']

    def test_message_bulk_get_negative(self):
        """GET more messages by id than allowed in a single request.

        By default, max messages that can be fetched in a single
        request is 20.
        """

        url = (self.message_url + '?ids='
               + ','.join(str(i) for i in
                          range(self.limits.max_messages_per_page + 1)))

        result = self.client.get(url)

        self.assertEqual(result.status_code, 400)

    test_message_bulk_get_negative.tags = ['negative']

    def test_get_messages_malformed_marker(self):
        """Get messages with non-existing marker."""
        url = self.message_url + '?marker=invalid'

        result = self.client.get(url, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertSchema(result.json(), 'message_list')

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
        self.assertEqual(result.status_code, 404)

    test_query_non_existing_message_set.tags = ['negative']

    def test_delete_non_existing_message(self):
        """Delete Non Existing Message."""
        path = '/non-existing-message'
        result = self.client.delete(path)
        self.assertEqual(result.status_code, 204)

    test_delete_non_existing_message.tags = ['negative']

    def test_message_bad_header_single_insert(self):
        """Insert Single Message into the Queue.

        This should fail because of the lack of a Client-ID header
        """

        self.skipTest("Not supported")
        del self.client.headers["Client-ID"]
        doc = helpers.create_message_body(messagecount=1)

        result = self.client.post(data=doc)
        self.assertEqual(result.status_code, 400)

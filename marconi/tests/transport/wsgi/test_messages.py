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

import json
import os

import falcon
from testtools import matchers

from marconi.common import config
from marconi.tests.transport.wsgi import base


class MessagesBaseTest(base.TestBase):

    def setUp(self):
        super(MessagesBaseTest, self).setUp()

        self.wsgi_cfg = config.namespace(
            'drivers:transport:wsgi').from_options()

        self.project_id = '7e55e1a7e'
        self.queue_path = '/v1/queues/fizbit'

        doc = '{"_ttl": 60}'
        self.simulate_put(self.queue_path, self.project_id, body=doc)

        self.headers = {
            'Client-ID': '30387f00',
        }

    def tearDown(self):
        self.simulate_delete(self.queue_path, self.project_id)
        super(MessagesBaseTest, self).tearDown()

    def _test_post(self, sample_messages):
        sample_doc = json.dumps(sample_messages)

        messages_path = self.queue_path + '/messages'
        result = self.simulate_post(messages_path, self.project_id,
                                    body=sample_doc, headers=self.headers)
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        result_doc = json.loads(result[0])

        msg_ids = self._get_msg_ids(self.srmock.headers_dict)
        self.assertEquals(len(msg_ids), len(sample_messages))

        expected_resources = [unicode(messages_path + '/' + id)
                              for id in msg_ids]
        self.assertEquals(expected_resources, result_doc['resources'])
        self.assertFalse(result_doc['partial'])

        self.assertEquals(len(msg_ids), len(sample_messages))

        lookup = dict([(m['ttl'], m['body']) for m in sample_messages])

        # Test GET on the message resource directly
        for msg_id in msg_ids:
            message_uri = messages_path + '/' + msg_id

            # Wrong project ID
            self.simulate_get(message_uri, '777777')
            self.assertEquals(self.srmock.status, falcon.HTTP_404)

            # Correct project ID
            result = self.simulate_get(message_uri, self.project_id)
            self.assertEquals(self.srmock.status, falcon.HTTP_200)
            self.assertEquals(self.srmock.headers_dict['Content-Location'],
                              message_uri)

            message = json.loads(result[0])
            self.assertEquals(message['href'], message_uri)
            self.assertEquals(message['body'], lookup[message['ttl']])

        # Test bulk GET
        query_string = 'ids=' + ','.join(msg_ids)
        result = self.simulate_get(messages_path, self.project_id,
                                   query_string=query_string)

        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        result_doc = json.loads(result[0])
        expected_ttls = set(m['ttl'] for m in sample_messages)
        actual_ttls = set(m['ttl'] for m in result_doc)
        self.assertFalse(expected_ttls - actual_ttls)

    def test_exceeded_payloads(self):
        # Get a valid message id
        path = self.queue_path + '/messages'
        self._post_messages(path)

        msg_id = self._get_msg_id(self.srmock.headers_dict)

        # Posting restriction
        self._post_messages(path, repeat=23)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        # Bulk GET restriction
        query_string = 'ids=' + ','.join([msg_id] * 21)
        self.simulate_get(path, self.project_id, query_string=query_string)

        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        # Listing restriction
        self.simulate_get(path, self.project_id,
                          query_string='limit=21',
                          headers=self.headers)

        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        # Bulk deletion restriction
        query_string = 'ids=' + ','.join([msg_id] * 22)
        self.simulate_delete(path, self.project_id, query_string=query_string)

        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_post_single(self):
        sample_messages = [
            {'body': {'key': 'value'}, 'ttl': 200},
        ]

        self._test_post(sample_messages)

    def test_post_multiple(self):
        sample_messages = [
            {'body': 239, 'ttl': 100},
            {'body': {'key': 'value'}, 'ttl': 200},
            {'body': [1, 3], 'ttl': 300},
        ]

        self._test_post(sample_messages)

    def test_post_to_missing_queue(self):
        self._post_messages('/v1/queues/nonexistent/messages')
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_post_bad_message(self):
        messages_path = self.queue_path + '/messages'

        for document in (None, '[', '[]', '{}', '.'):
            self.simulate_post(messages_path,
                               body=document,
                               headers=self.headers)

            self.assertEquals(self.srmock.status, falcon.HTTP_400)

        # Unacceptable TTL
        for ttl in (-1, 59, 1209601):
            self.simulate_post(messages_path,
                               body=json.dumps([{'ttl': ttl,
                                                 'body': None}]),
                               headers=self.headers)
            self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_exceeded_message_posting(self):
        # Total (raw request) size
        doc = json.dumps([{'body': "some body", 'ttl': 100}] * 20, indent=4)
        long_doc = doc + (' ' *
                          (self.wsgi_cfg.content_max_length - len(doc) + 1))

        self.simulate_post(self.queue_path + '/messages',
                           body=long_doc,
                           headers=self.headers)

        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_unsupported_json(self):
        for document in ('{"overflow": 9223372036854775808}',
                         '{"underflow": -9223372036854775809}'):
            self.simulate_post(self.queue_path + '/messages',
                               body=document,
                               headers=self.headers)

            self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_delete(self):
        path = self.queue_path + '/messages'
        self._post_messages(path)

        msg_id = self._get_msg_id(self.srmock.headers_dict)

        self.simulate_get(path + '/' + msg_id, self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

        self.simulate_delete(path + '/' + msg_id, self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        self.simulate_get(path + '/' + msg_id, self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

        # Safe to delete non-existing ones
        self.simulate_delete(path + '/' + msg_id, self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

    def test_bulk_delete(self):
        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=5)
        [target, params] = self.srmock.headers_dict['Location'].split('?')

        # Deleting the whole collection is denied
        self.simulate_delete(path, self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        self.simulate_delete(target, self.project_id, query_string=params)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        self.simulate_get(target, self.project_id, query_string=params)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Safe to delete non-existing ones
        self.simulate_delete(target, self.project_id, query_string=params)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Even after the queue is gone
        self.simulate_delete(self.queue_path, self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        self.simulate_delete(target, self.project_id, query_string=params)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

    def test_list(self):
        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=10)

        query_string = 'limit=3&echo=true'
        body = self.simulate_get(path, self.project_id,
                                 query_string=query_string,
                                 headers=self.headers)

        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        self.assertEquals(self.srmock.headers_dict['Content-Location'],
                          path + '?' + query_string)

        cnt = 0
        while self.srmock.status == falcon.HTTP_200:
            contents = json.loads(body[0])
            [target, params] = contents['links'][0]['href'].split('?')

            for msg in contents['messages']:
                self.simulate_get(msg['href'], self.project_id)
                self.assertEquals(self.srmock.status, falcon.HTTP_200)

            body = self.simulate_get(target, self.project_id,
                                     query_string=params,
                                     headers=self.headers)
            cnt += 1

        self.assertEquals(cnt, 4)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Stats
        body = self.simulate_get(self.queue_path + '/stats', self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

        message_stats = json.loads(body[0])['messages']
        self.assertEquals(self.srmock.headers_dict['Content-Location'],
                          self.queue_path + '/stats')

        # NOTE(kgriffs): The other parts of the stats are tested
        # in tests.storage.base and so are not repeated here.
        expected_pattern = self.queue_path + '/messages/[^/]+$'
        for message_stat_name in ('oldest', 'newest'):
            self.assertThat(message_stats[message_stat_name]['href'],
                            matchers.MatchesRegex(expected_pattern))

        # NOTE(kgriffs): Try to get messages for a missing queue
        self.simulate_get('/v1/queues/nonexistent/messages', self.project_id,
                          headers=self.headers)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

    def test_list_with_bad_marker(self):
        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=5)

        query_string = 'limit=3&echo=true&marker=sfhlsfdjh2048'
        self.simulate_get(path, self.project_id,
                          query_string=query_string,
                          headers=self.headers)

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_no_uuid(self):
        path = self.queue_path + '/messages'

        self.simulate_post(path, '7e7e7e', body='[{"body": 0, "ttl": 100}]')

        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        self.simulate_get(path, '7e7e7e')
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

    # NOTE(cpp-cabrera): regression test against bug #1210633
    def test_when_claim_deleted_then_messages_unclaimed(self):
        path = self.queue_path
        self._post_messages(path + '/messages', repeat=5)

        # post claim
        self.simulate_post(path + '/claims', self.project_id,
                           body='{"ttl": 100, "grace": 100}')
        self.assertEquals(self.srmock.status, falcon.HTTP_201)
        location = self.srmock.headers_dict['Location']

        # release claim
        self.simulate_delete(location, self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # get unclaimed messages
        self.simulate_get(path + '/messages', self.project_id,
                          query_string='echo=true',
                          headers=self.headers)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

    # NOTE(cpp-cabrera): regression test against bug #1203842
    def test_get_nonexistent_message_404s(self):
        path = '/v1/queues/notthere'

        self.simulate_get(path + '/messages/a')
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_get_multiple_invalid_messages_204s(self):
        path = '/v1/queues/notthere'

        self.simulate_get(path + '/messages', query_string='ids=a,b,c')
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

    def test_delete_multiple_invalid_messages_204s(self):
        path = '/v1/queues/notthere'

        self.simulate_delete(path + '/messages', query_string='ids=a,b,c')
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

    def test_delete_message_with_invalid_claim_doesnt_delete_message(self):
        path = self.queue_path
        resp = self._post_messages(path + '/messages', 1)
        location = json.loads(resp[0])['resources'][0]

        self.simulate_delete(location, query_string='claim_id=invalid')
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        self.simulate_get(location, self.project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

    def _post_messages(self, target, repeat=1):
        doc = json.dumps([{'body': 239, 'ttl': 300}] * repeat)
        return self.simulate_post(target, self.project_id, body=doc,
                                  headers=self.headers)

    def _get_msg_id(self, headers):
        return self._get_msg_ids(headers)[0]

    def _get_msg_ids(self, headers):
        return headers['Location'].rsplit('=', 1)[-1].split(',')


class MessagesSQLiteTests(MessagesBaseTest):

    config_filename = 'wsgi_sqlite.conf'


class MessagesMongoDBTests(MessagesBaseTest):

    config_filename = 'wsgi_mongodb.conf'

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance running')

        super(MessagesMongoDBTests, self).setUp()


class MessagesFaultyDriverTests(base.TestBaseFaulty):

    config_filename = 'wsgi_faulty.conf'

    def test_simple(self):
        project_id = 'xyz'
        path = '/v1/queues/fizbit/messages'
        doc = '[{"body": 239, "ttl": 100}]'
        headers = {
            'Client-ID': '30387f00',
        }

        self.simulate_post(path, project_id,
                           body=doc,
                           headers=headers)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        self.simulate_get(path, project_id,
                          headers=headers)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        self.simulate_get(path + '/nonexistent', project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

        self.simulate_delete(path + '/nada', project_id)
        self.assertEquals(self.srmock.status, falcon.HTTP_503)

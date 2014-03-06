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

import datetime
import json
import uuid

import ddt
import falcon
import mock
import six
from testtools import matchers

from . import base  # noqa
from marconi.openstack.common import timeutils
from marconi.queues.transport import validation
from marconi import tests as testing


@ddt.ddt
class MessagesBaseTest(base.TestBase):

    def setUp(self):
        super(MessagesBaseTest, self).setUp()

        if self.conf.sharding:
            for i in range(4):
                uri = self.conf['drivers:storage:mongodb'].uri
                doc = {'weight': 100, 'uri': uri}
                self.simulate_put(self.url_prefix + '/shards/' + str(i),
                                  body=json.dumps(doc))
                self.assertEqual(self.srmock.status, falcon.HTTP_201)

        self.project_id = '7e55e1a7e'

        # TODO(kgriffs): Add support in self.simulate_* for a "base path"
        # so that we don't have to concatenate against self.url_prefix
        # all over the place.
        self.queue_path = self.url_prefix + '/queues/fizbit'
        self.messages_path = self.queue_path + '/messages'

        doc = '{"_ttl": 60}'
        self.simulate_put(self.queue_path, self.project_id, body=doc)

        self.headers = {
            'Client-ID': str(uuid.uuid4()),
        }

    def tearDown(self):
        self.simulate_delete(self.queue_path, self.project_id)
        if self.conf.sharding:
            for i in range(4):
                self.simulate_delete(self.url_prefix + '/shards/' + str(i))

        super(MessagesBaseTest, self).tearDown()

    def _test_post(self, sample_messages):
        sample_doc = json.dumps(sample_messages)

        result = self.simulate_post(self.messages_path, self.project_id,
                                    body=sample_doc, headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        result_doc = json.loads(result[0])

        msg_ids = self._get_msg_ids(self.srmock.headers_dict)
        self.assertEqual(len(msg_ids), len(sample_messages))

        expected_resources = [six.text_type(self.messages_path + '/' + id)
                              for id in msg_ids]
        self.assertEqual(expected_resources, result_doc['resources'])
        self.assertFalse(result_doc['partial'])

        self.assertEqual(len(msg_ids), len(sample_messages))

        lookup = dict([(m['ttl'], m['body']) for m in sample_messages])

        # Test GET on the message resource directly
        # NOTE(cpp-cabrera): force the passing of time to age a message
        timeutils_utcnow = 'marconi.openstack.common.timeutils.utcnow'
        now = timeutils.utcnow() + datetime.timedelta(seconds=10)
        with mock.patch(timeutils_utcnow) as mock_utcnow:
            mock_utcnow.return_value = now
            for msg_id in msg_ids:
                message_uri = self.messages_path + '/' + msg_id

                # Wrong project ID
                self.simulate_get(message_uri, '777777')
                self.assertEqual(self.srmock.status, falcon.HTTP_404)

                # Correct project ID
                result = self.simulate_get(message_uri, self.project_id)
                self.assertEqual(self.srmock.status, falcon.HTTP_200)
                self.assertEqual(self.srmock.headers_dict['Content-Location'],
                                 message_uri)

                # Check message properties
                message = json.loads(result[0])
                self.assertEqual(message['href'], message_uri)
                self.assertEqual(message['body'], lookup[message['ttl']])

                # no negative age
                # NOTE(cpp-cabrera): testtools lacks GreaterThanEqual on py26
                self.assertThat(message['age'],
                                matchers.GreaterThan(-1))

        # Test bulk GET
        query_string = 'ids=' + ','.join(msg_ids)
        result = self.simulate_get(self.messages_path, self.project_id,
                                   query_string=query_string)

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_doc = json.loads(result[0])
        expected_ttls = set(m['ttl'] for m in sample_messages)
        actual_ttls = set(m['ttl'] for m in result_doc)
        self.assertFalse(expected_ttls - actual_ttls)

    def test_exceeded_payloads(self):
        # Get a valid message id
        self._post_messages(self.messages_path)
        msg_id = self._get_msg_id(self.srmock.headers_dict)

        # Bulk GET restriction
        query_string = 'ids=' + ','.join([msg_id] * 21)
        self.simulate_get(self.messages_path, self.project_id,
                          query_string=query_string)

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        # Listing restriction
        self.simulate_get(self.messages_path, self.project_id,
                          query_string='limit=21',
                          headers=self.headers)

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        # Bulk deletion restriction
        query_string = 'ids=' + ','.join([msg_id] * 22)
        self.simulate_delete(self.messages_path, self.project_id,
                             query_string=query_string)

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

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

    def test_post_to_non_ascii_queue(self):
        # NOTE(kgriffs): This test verifies that routes with
        # embedded queue name params go through the validation
        # hook, regardless of the target resource.

        path = self.url_prefix + u'/queues/non-ascii-n\u0153me/messages'

        if six.PY2:
            path = path.encode('utf-8')

        self._post_messages(path)
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_post_with_long_queue_name(self):
        # NOTE(kgriffs): This test verifies that routes with
        # embedded queue name params go through the validation
        # hook, regardless of the target resource.

        queues_path = self.url_prefix + '/queues/'

        game_title = 'v' * validation.QUEUE_NAME_MAX_LEN
        self._post_messages(queues_path + game_title + '/messages')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

        game_title += 'v'
        self._post_messages(queues_path + game_title + '/messages')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_post_to_missing_queue(self):
        self._post_messages(self.url_prefix + '/queues/nonexistent/messages')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_get_from_missing_queue(self):
        self.simulate_get(self.url_prefix + '/queues/nonexistent/messages',
                          self.project_id,
                          headers={'Client-ID':
                                   'dfcd3238-425c-11e3-8a80-28cfe91478b9'})
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    @ddt.data('', '0xdeadbeef', '550893e0-2b6e-11e3-835a-5cf9dd72369')
    def test_bad_client_id(self, text_id):
        self.simulate_post(self.queue_path + '/messages',
                           body='{"ttl": 60, "body": ""}',
                           headers={'Client-ID': text_id})

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_get(self.queue_path + '/messages',
                          query_string='limit=3&echo=true',
                          headers={'Client-ID': text_id})

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(None, '[', '[]', '{}', '.')
    def test_post_bad_message(self, document):
        self.simulate_post(self.queue_path + '/messages',
                           body=document,
                           headers=self.headers)

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 59, 1209601)
    def test_unacceptable_ttl(self, ttl):
        self.simulate_post(self.queue_path + '/messages',
                           body=json.dumps([{'ttl': ttl,
                                             'body': None}]),
                           headers=self.headers)

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_exceeded_message_posting(self):
        # Total (raw request) size
        doc = json.dumps([{'body': "some body", 'ttl': 100}] * 20, indent=4)

        max_len = self.transport_cfg.max_message_size
        long_doc = doc + (' ' * (max_len - len(doc) + 1))

        self.simulate_post(self.queue_path + '/messages',
                           body=long_doc,
                           headers=self.headers)

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data('{"overflow": 9223372036854775808}',
              '{"underflow": -9223372036854775809}')
    def test_unsupported_json(self, document):
        self.simulate_post(self.queue_path + '/messages',
                           body=document,
                           headers=self.headers)

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_delete(self):
        self._post_messages(self.messages_path)
        msg_id = self._get_msg_id(self.srmock.headers_dict)
        target = self.messages_path + '/' + msg_id

        self.simulate_get(target, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        self.simulate_delete(target, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        self.simulate_get(target, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

        # Safe to delete non-existing ones
        self.simulate_delete(target, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def test_bulk_delete(self):
        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=5)
        [target, params] = self.srmock.headers_dict['location'].split('?')

        # Deleting the whole collection is denied
        self.simulate_delete(path, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_delete(target, self.project_id, query_string=params)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        self.simulate_get(target, self.project_id, query_string=params)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Safe to delete non-existing ones
        self.simulate_delete(target, self.project_id, query_string=params)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Even after the queue is gone
        self.simulate_delete(self.queue_path, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        self.simulate_delete(target, self.project_id, query_string=params)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def test_list(self):
        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=10)

        query_string = 'limit=3&echo=true'
        body = self.simulate_get(path, self.project_id,
                                 query_string=query_string,
                                 headers=self.headers)

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertEqual(self.srmock.headers_dict['Content-Location'],
                         path + '?' + query_string)

        cnt = 0
        while self.srmock.status == falcon.HTTP_200:
            contents = json.loads(body[0])
            [target, params] = contents['links'][0]['href'].split('?')

            for msg in contents['messages']:
                self.simulate_get(msg['href'], self.project_id)
                self.assertEqual(self.srmock.status, falcon.HTTP_200)

            body = self.simulate_get(target, self.project_id,
                                     query_string=params,
                                     headers=self.headers)
            cnt += 1

        self.assertEqual(cnt, 4)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Stats
        body = self.simulate_get(self.queue_path + '/stats', self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        message_stats = json.loads(body[0])['messages']
        self.assertEqual(self.srmock.headers_dict['Content-Location'],
                         self.queue_path + '/stats')

        # NOTE(kgriffs): The other parts of the stats are tested
        # in tests.storage.base and so are not repeated here.
        expected_pattern = self.queue_path + '/messages/[^/]+$'
        for message_stat_name in ('oldest', 'newest'):
            self.assertThat(message_stats[message_stat_name]['href'],
                            matchers.MatchesRegex(expected_pattern))

        # NOTE(kgriffs): Try to get messages for a missing queue
        self.simulate_get(self.url_prefix + '/queues/nonexistent/messages',
                          self.project_id,
                          headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def test_list_with_bad_marker(self):
        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=5)

        query_string = 'limit=3&echo=true&marker=sfhlsfdjh2048'
        self.simulate_get(path, self.project_id,
                          query_string=query_string,
                          headers=self.headers)

        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def test_no_uuid(self):
        path = self.queue_path + '/messages'

        self.simulate_post(path, '7e7e7e', body='[{"body": 0, "ttl": 100}]')

        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_get(path, '7e7e7e')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    # NOTE(cpp-cabrera): regression test against bug #1210633
    def test_when_claim_deleted_then_messages_unclaimed(self):
        path = self.queue_path
        self._post_messages(path + '/messages', repeat=5)

        # post claim
        self.simulate_post(path + '/claims', self.project_id,
                           body='{"ttl": 100, "grace": 100}')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        location = self.srmock.headers_dict['location']

        # release claim
        self.simulate_delete(location, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # get unclaimed messages
        self.simulate_get(path + '/messages', self.project_id,
                          query_string='echo=true',
                          headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

    # NOTE(cpp-cabrera): regression test against bug #1203842
    def test_get_nonexistent_message_404s(self):
        path = self.url_prefix + '/queues/notthere/messages/a'
        self.simulate_get(path)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_get_multiple_invalid_messages_204s(self):
        path = self.url_prefix + '/queues/notthere/messages'
        self.simulate_get(path, query_string='ids=a,b,c')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def test_delete_multiple_invalid_messages_204s(self):
        path = self.url_prefix + '/queues/notthere/messages'
        self.simulate_delete(path, query_string='ids=a,b,c')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def test_delete_message_with_invalid_claim_doesnt_delete_message(self):
        path = self.queue_path
        resp = self._post_messages(path + '/messages', 1)
        location = json.loads(resp[0])['resources'][0]

        self.simulate_delete(location, query_string='claim_id=invalid')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        self.simulate_get(location, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

    def test_no_duplicated_messages_path_in_href(self):
        """Fixes bug 1240897
        """
        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=1)

        msg_id = self._get_msg_id(self.srmock.headers_dict)

        query_string = 'ids=%s' % msg_id
        body = self.simulate_get(path, self.project_id,
                                 query_string=query_string,
                                 headers=self.headers)
        messages = json.loads(body[0])

        self.assertNotIn(self.queue_path + '/messages/messages',
                         messages[0]['href'])

    def _post_messages(self, target, repeat=1):
        doc = json.dumps([{'body': 239, 'ttl': 300}] * repeat)
        return self.simulate_post(target, self.project_id, body=doc,
                                  headers=self.headers)

    def _get_msg_id(self, headers):
        return self._get_msg_ids(headers)[0]

    def _get_msg_ids(self, headers):
        return headers['location'].rsplit('=', 1)[-1].split(',')


class TestMessagesSqlalchemy(MessagesBaseTest):

    config_file = 'wsgi_sqlalchemy.conf'


class TestMessagesMongoDB(MessagesBaseTest):

    config_file = 'wsgi_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestMessagesMongoDB, self).setUp()

    def tearDown(self):
        super(TestMessagesMongoDB, self).tearDown()


class TestMessagesMongoDBSharded(MessagesBaseTest):

    config_file = 'wsgi_mongodb_sharded.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestMessagesMongoDBSharded, self).setUp()

    def tearDown(self):
        super(TestMessagesMongoDBSharded, self).tearDown()

    # TODO(cpp-cabrera): remove this skipTest once sharded queue
    # listing is implemented
    def test_list(self):
        self.skipTest("Need to implement sharded queue listing.")


class TestMessagesFaultyDriver(base.TestBaseFaulty):

    config_file = 'wsgi_faulty.conf'

    def test_simple(self):
        project_id = 'xyz'
        path = self.url_prefix + '/queues/fizbit/messages'
        doc = '[{"body": 239, "ttl": 100}]'
        headers = {
            'Client-ID': str(uuid.uuid4()),
        }

        self.simulate_post(path, project_id,
                           body=doc,
                           headers=headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

        self.simulate_get(path, project_id,
                          headers=headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

        self.simulate_get(path + '/nonexistent', project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

        self.simulate_delete(path + '/nada', project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

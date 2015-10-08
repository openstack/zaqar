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
import uuid

import ddt
import falcon
import mock
from oslo_serialization import jsonutils
from oslo_utils import timeutils
import six
from testtools import matchers

from zaqar import tests as testing
from zaqar.tests.unit.transport.wsgi import base
from zaqar.transport import validation


@ddt.ddt
class TestMessagesMongoDB(base.V1_1Base):

    config_file = 'wsgi_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestMessagesMongoDB, self).setUp()

        self.default_message_ttl = self.boot.transport._defaults.message_ttl

        if self.conf.pooling:
            for i in range(4):
                uri = "%s/%s" % (self.mongodb_url, str(i))
                doc = {'weight': 100, 'uri': uri}
                self.simulate_put(self.url_prefix + '/pools/' + str(i),
                                  body=jsonutils.dumps(doc))
                self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self.project_id = '7e55e1a7e'
        self.headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': self.project_id
        }

        # TODO(kgriffs): Add support in self.simulate_* for a "base path"
        # so that we don't have to concatenate against self.url_prefix
        # all over the place.
        self.queue_path = self.url_prefix + '/queues/fizbit'
        self.messages_path = self.queue_path + '/messages'

        doc = '{"_ttl": 60}'
        self.simulate_put(self.queue_path, body=doc, headers=self.headers)

    def tearDown(self):
        self.simulate_delete(self.queue_path, headers=self.headers)
        if self.conf.pooling:
            for i in range(4):
                self.simulate_delete(self.url_prefix + '/pools/' + str(i),
                                     headers=self.headers)

        super(TestMessagesMongoDB, self).tearDown()

    def test_name_restrictions(self):
        sample_messages = [
            {'body': {'key': 'value'}, 'ttl': 200},
        ]
        messages_path = self.url_prefix + '/queues/%s/messages'
        sample_doc = jsonutils.dumps({'messages': sample_messages})

        self.simulate_post(messages_path % 'Nice-Boat_2',
                           body=sample_doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self.simulate_post(messages_path % 'Nice-Bo@t',
                           body=sample_doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_post(messages_path % ('_niceboat' * 8),
                           body=sample_doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def _test_post(self, sample_messages):
        sample_doc = jsonutils.dumps({'messages': sample_messages})

        result = self.simulate_post(self.messages_path,
                                    body=sample_doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        result_doc = jsonutils.loads(result[0])

        msg_ids = self._get_msg_ids(self.srmock.headers_dict)
        self.assertEqual(len(sample_messages), len(msg_ids))

        expected_resources = [six.text_type(self.messages_path + '/' + id)
                              for id in msg_ids]
        self.assertEqual(expected_resources, result_doc['resources'])

        # NOTE(kgriffs): As of v1.1, "partial" is no longer given
        # in the response document.
        self.assertNotIn('partial', result_doc)

        self.assertEqual(len(sample_messages), len(msg_ids))

        lookup = dict([(m['ttl'], m['body']) for m in sample_messages])

        # Test GET on the message resource directly
        # NOTE(cpp-cabrera): force the passing of time to age a message
        timeutils_utcnow = 'oslo_utils.timeutils.utcnow'
        now = timeutils.utcnow() + datetime.timedelta(seconds=10)
        with mock.patch(timeutils_utcnow) as mock_utcnow:
            mock_utcnow.return_value = now
            for msg_id in msg_ids:
                message_uri = self.messages_path + '/' + msg_id

                headers = self.headers.copy()
                headers['X-Project-ID'] = '777777'
                # Wrong project ID
                self.simulate_get(message_uri, headers=headers)
                self.assertEqual(falcon.HTTP_404, self.srmock.status)

                # Correct project ID
                result = self.simulate_get(message_uri, headers=self.headers)
                self.assertEqual(falcon.HTTP_200, self.srmock.status)

                # Check message properties
                message = jsonutils.loads(result[0])
                self.assertEqual(message_uri, message['href'])
                self.assertEqual(lookup[message['ttl']], message['body'])
                self.assertEqual(msg_id, message['id'])

                # no negative age
                # NOTE(cpp-cabrera): testtools lacks GreaterThanEqual on py26
                self.assertThat(message['age'],
                                matchers.GreaterThan(-1))

        # Test bulk GET
        query_string = 'ids=' + ','.join(msg_ids)
        result = self.simulate_get(self.messages_path,
                                   query_string=query_string,
                                   headers=self.headers)

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        result_doc = jsonutils.loads(result[0])
        expected_ttls = set(m['ttl'] for m in sample_messages)
        actual_ttls = set(m['ttl'] for m in result_doc['messages'])
        self.assertFalse(expected_ttls - actual_ttls)
        actual_ids = set(m['id'] for m in result_doc['messages'])
        self.assertFalse(set(msg_ids) - actual_ids)

    def test_exceeded_payloads(self):
        # Get a valid message id
        self._post_messages(self.messages_path)
        msg_id = self._get_msg_id(self.srmock.headers_dict)

        # Bulk GET restriction
        query_string = 'ids=' + ','.join([msg_id] * 21)
        self.simulate_get(self.messages_path,
                          query_string=query_string, headers=self.headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Listing restriction
        self.simulate_get(self.messages_path,
                          query_string='limit=21',
                          headers=self.headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Bulk deletion restriction
        query_string = 'ids=' + ','.join([msg_id] * 22)
        self.simulate_delete(self.messages_path,
                             query_string=query_string, headers=self.headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

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

    def test_post_optional_ttl(self):
        sample_messages = {
            'messages': [
                {'body': 239},
                {'body': {'key': 'value'}, 'ttl': 200},
            ],
        }

        # Manually check default TTL is max from config

        sample_doc = jsonutils.dumps(sample_messages)
        result = self.simulate_post(self.messages_path,
                                    body=sample_doc, headers=self.headers)

        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        result_doc = jsonutils.loads(result[0])

        href = result_doc['resources'][0]
        result = self.simulate_get(href, headers=self.headers)
        message = jsonutils.loads(result[0])

        self.assertEqual(self.default_message_ttl, message['ttl'])

    def test_post_to_non_ascii_queue(self):
        # NOTE(kgriffs): This test verifies that routes with
        # embedded queue name params go through the validation
        # hook, regardless of the target resource.

        path = self.url_prefix + u'/queues/non-ascii-n\u0153me/messages'

        if six.PY2:
            path = path.encode('utf-8')

        self._post_messages(path)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_post_with_long_queue_name(self):
        # NOTE(kgriffs): This test verifies that routes with
        # embedded queue name params go through the validation
        # hook, regardless of the target resource.

        queues_path = self.url_prefix + '/queues/'

        game_title = 'v' * validation.QUEUE_NAME_MAX_LEN
        self.addCleanup(
            self.simulate_delete, queues_path + game_title,
            headers=self.headers)
        self._post_messages(queues_path + game_title + '/messages')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        game_title += 'v'
        self._post_messages(queues_path + game_title + '/messages')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_post_to_missing_queue(self):
        self.addCleanup(
            self.simulate_delete, self.url_prefix + '/queues/nonexistent',
            headers=self.headers)
        self._post_messages(self.url_prefix + '/queues/nonexistent/messages')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_get_from_missing_queue(self):
        body = self.simulate_get(self.url_prefix +
                                 '/queues/nonexistent/messages',
                                 headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self._empty_message_list(body)

    @ddt.data('', '0xdeadbeef', '550893e0-2b6e-11e3-835a-5cf9dd72369')
    def test_bad_client_id(self, text_id):
        self.simulate_post(self.queue_path + '/messages',
                           body='{"ttl": 60, "body": ""}',
                           headers={'Client-ID': text_id})

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_get(self.queue_path + '/messages',
                          query_string='limit=3&echo=true',
                          headers={'Client-ID': text_id})

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data(None, '[', '[]', '{}', '.')
    def test_post_bad_message(self, document):
        self.simulate_post(self.queue_path + '/messages',
                           body=document,
                           headers=self.headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data(-1, 59, 1209601)
    def test_unacceptable_ttl(self, ttl):
        doc = {'messages': [{'ttl': ttl, 'body': None}]}

        self.simulate_post(self.queue_path + '/messages',
                           body=jsonutils.dumps(doc),
                           headers=self.headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_exceeded_message_posting(self):
        # Total (raw request) size
        doc = {'messages': [{'body': "some body", 'ttl': 100}] * 20}
        body = jsonutils.dumps(doc, indent=4)

        max_len = self.transport_cfg.max_messages_post_size
        long_body = body + (' ' * (max_len - len(body) + 1))

        self.simulate_post(self.queue_path + '/messages',
                           body=long_body,
                           headers=self.headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data('{"overflow": 9223372036854775808}',
              '{"underflow": -9223372036854775809}')
    def test_unsupported_json(self, document):
        self.simulate_post(self.queue_path + '/messages',
                           body=document,
                           headers=self.headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_delete(self):
        self._post_messages(self.messages_path)
        msg_id = self._get_msg_id(self.srmock.headers_dict)
        target = self.messages_path + '/' + msg_id

        self.simulate_get(target, headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        self.simulate_delete(target, headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.simulate_get(target, headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Safe to delete non-existing ones
        self.simulate_delete(target, headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_bulk_delete(self):
        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=5)
        [target, params] = self.srmock.headers_dict['location'].split('?')

        # Deleting the whole collection is denied
        self.simulate_delete(path, headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_delete(target, query_string=params, headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.simulate_get(target, query_string=params, headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Safe to delete non-existing ones
        self.simulate_delete(target, query_string=params, headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Even after the queue is gone
        self.simulate_delete(self.queue_path, headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.simulate_delete(target, query_string=params, headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_list(self):
        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=10)

        query_string = 'limit=3&echo=true'
        body = self.simulate_get(path,
                                 query_string=query_string,
                                 headers=self.headers)

        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        cnt = 0
        while jsonutils.loads(body[0])['messages'] != []:
            contents = jsonutils.loads(body[0])
            [target, params] = contents['links'][0]['href'].split('?')

            for msg in contents['messages']:
                self.simulate_get(msg['href'], headers=self.headers)
                self.assertEqual(falcon.HTTP_200, self.srmock.status)

            body = self.simulate_get(target,
                                     query_string=params,
                                     headers=self.headers)
            cnt += 1

        self.assertEqual(4, cnt)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self._empty_message_list(body)

        # Stats
        body = self.simulate_get(self.queue_path + '/stats',
                                 headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        message_stats = jsonutils.loads(body[0])['messages']

        # NOTE(kgriffs): The other parts of the stats are tested
        # in tests.storage.base and so are not repeated here.
        expected_pattern = self.queue_path + '/messages/[^/]+$'
        for message_stat_name in ('oldest', 'newest'):
            self.assertThat(message_stats[message_stat_name]['href'],
                            matchers.MatchesRegex(expected_pattern))

        # NOTE(kgriffs): Try to get messages for a missing queue
        body = self.simulate_get(self.url_prefix +
                                 '/queues/nonexistent/messages',
                                 headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self._empty_message_list(body)

    def test_list_with_bad_marker(self):
        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=5)

        query_string = 'limit=3&echo=true&marker=sfhlsfdjh2048'
        body = self.simulate_get(path,
                                 query_string=query_string,
                                 headers=self.headers)

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self._empty_message_list(body)

    def test_no_uuid(self):
        headers = {
            'Client-ID': "textid",
            'X-Project-ID': '7e7e7e'
        }
        path = self.queue_path + '/messages'

        self.simulate_post(path, body='[{"body": 0, "ttl": 100}]',
                           headers=headers)

        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_get(path, headers=headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_get_claimed_contains_claim_id_in_href(self):
        path = self.queue_path
        res = self._post_messages(path + '/messages', repeat=5)
        for url in jsonutils.loads(res[0])['resources']:
            message = self.simulate_get(url)
            self.assertNotIn('claim_id', jsonutils.loads(message[0])['href'])

        self.simulate_post(path + '/claims',
                           body='{"ttl": 100, "grace": 100}',
                           headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        for url in jsonutils.loads(res[0])['resources']:
            message = self.simulate_get(url)
            self.assertIn('claim_id', jsonutils.loads(message[0])['href'])

    # NOTE(cpp-cabrera): regression test against bug #1210633
    def test_when_claim_deleted_then_messages_unclaimed(self):
        path = self.queue_path
        self._post_messages(path + '/messages', repeat=5)

        # post claim
        self.simulate_post(path + '/claims',
                           body='{"ttl": 100, "grace": 100}',
                           headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        location = self.srmock.headers_dict['location']

        # release claim
        self.simulate_delete(location, headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # get unclaimed messages
        self.simulate_get(path + '/messages',
                          query_string='echo=true',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    # NOTE(cpp-cabrera): regression test against bug #1203842
    def test_get_nonexistent_message_404s(self):
        path = self.url_prefix + '/queues/notthere/messages/a'
        self.simulate_get(path, headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_get_multiple_invalid_messages_404s(self):
        path = self.url_prefix + '/queues/notthere/messages'
        self.simulate_get(path, query_string='ids=a,b,c',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_delete_multiple_invalid_messages_204s(self):
        path = self.url_prefix + '/queues/notthere/messages'
        self.simulate_delete(path, query_string='ids=a,b,c',
                             headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_delete_message_with_invalid_claim_doesnt_delete_message(self):
        path = self.queue_path
        resp = self._post_messages(path + '/messages', 1)
        location = jsonutils.loads(resp[0])['resources'][0]

        self.simulate_delete(location, query_string='claim_id=invalid',
                             headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_get(location, headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_no_duplicated_messages_path_in_href(self):
        """Test for bug 1240897."""

        path = self.queue_path + '/messages'
        self._post_messages(path, repeat=1)

        msg_id = self._get_msg_id(self.srmock.headers_dict)

        query_string = 'ids=%s' % msg_id
        body = self.simulate_get(path,
                                 query_string=query_string,
                                 headers=self.headers)
        messages = jsonutils.loads(body[0])

        self.assertNotIn(self.queue_path + '/messages/messages',
                         messages['messages'][0]['href'])

    def _post_messages(self, target, repeat=1):
        doc = {'messages': [{'body': 239, 'ttl': 300}] * repeat}

        body = jsonutils.dumps(doc)
        return self.simulate_post(target, body=body, headers=self.headers)

    def _get_msg_id(self, headers):
        return self._get_msg_ids(headers)[0]

    def _get_msg_ids(self, headers):
        return headers['location'].rsplit('=', 1)[-1].split(',')

    @ddt.data(1, 2, 10)
    def test_pop(self, message_count):

        self._post_messages(self.messages_path, repeat=message_count)
        msg_id = self._get_msg_id(self.srmock.headers_dict)
        target = self.messages_path + '/' + msg_id

        self.simulate_get(target, self.project_id)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        query_string = 'pop=' + str(message_count)
        result = self.simulate_delete(self.messages_path, self.project_id,
                                      query_string=query_string)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        result_doc = jsonutils.loads(result[0])

        self.assertEqual(message_count, len(result_doc['messages']))

        self.simulate_get(target, self.project_id)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    @ddt.data('', 'pop=1000000', 'pop=10&ids=1', 'pop=-1')
    def test_pop_invalid(self, query_string):

        self.simulate_delete(self.messages_path, self.project_id,
                             query_string=query_string)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_pop_empty_queue(self):

        query_string = 'pop=1'
        result = self.simulate_delete(self.messages_path, self.project_id,
                                      query_string=query_string)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        result_doc = jsonutils.loads(result[0])
        self.assertEqual([], result_doc['messages'])

    def test_pop_single_message(self):

        self._post_messages(self.messages_path, repeat=5)
        msg_id = self._get_msg_id(self.srmock.headers_dict)
        target = self.messages_path + '/' + msg_id

        self.simulate_get(target, self.project_id)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Pop Single message from the queue
        query_string = 'pop=1'
        result = self.simulate_delete(self.messages_path, self.project_id,
                                      query_string=query_string)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Get messages from the queue & verify message count
        query_string = 'echo=True'
        result = self.simulate_get(self.messages_path, self.project_id,
                                   query_string=query_string,
                                   headers=self.headers)
        result_doc = jsonutils.loads(result[0])
        actual_msg_count = len(result_doc['messages'])
        expected_msg_count = 4
        self.assertEqual(expected_msg_count, actual_msg_count)


class TestMessagesMongoDBPooled(TestMessagesMongoDB):
    config_file = 'wsgi_mongodb_pooled.conf'

    # TODO(cpp-cabrera): remove this skipTest once pooled queue
    # listing is implemented
    def test_list(self):
        self.skipTest("Need to implement pooled queue listing.")


class TestMessagesFaultyDriver(base.V1_1BaseFaulty):
    config_file = 'wsgi_faulty.conf'

    def test_simple(self):
        project_id = 'xyz'
        path = self.url_prefix + '/queues/fizbit/messages'
        body = '{"messages": [{"body": 239, "ttl": 100}]}'
        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': project_id
        }

        self.simulate_post(path,
                           body=body,
                           headers=headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_get(path,
                          headers=headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_get(path + '/nonexistent', headers=headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_delete(path + '/nada', headers=headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

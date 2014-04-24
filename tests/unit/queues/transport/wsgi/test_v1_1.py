# Copyright (c) 2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
import uuid

import ddt
import falcon

from marconi.openstack.common import jsonutils
from marconi.tests.queues.transport.wsgi import base
from marconi.tests.queues.transport.wsgi import v1_1

# --------------------------------------------------------------------------
# Identical or just minor variations across versions
# --------------------------------------------------------------------------

URL_PREFIX = '/v1.1'


class TestAuth(v1_1.TestAuth):
    url_prefix = URL_PREFIX


class TestClaimsFaultyDriver(v1_1.TestClaimsFaultyDriver):
    url_prefix = URL_PREFIX


class TestClaimsMongoDB(v1_1.TestClaimsMongoDB):
    url_prefix = URL_PREFIX


class TestClaimsSqlalchemy(v1_1.TestClaimsSqlalchemy):
    url_prefix = URL_PREFIX


class TestDefaultLimits(v1_1.TestDefaultLimits):
    url_prefix = URL_PREFIX


class TestHomeDocument(v1_1.TestHomeDocument):
    url_prefix = URL_PREFIX


class TestMediaType(v1_1.TestMediaType):
    url_prefix = URL_PREFIX


class TestMessagesFaultyDriver(v1_1.TestMessagesFaultyDriver):
    url_prefix = URL_PREFIX


class TestMessagesMongoDB(v1_1.TestMessagesMongoDB):
    url_prefix = URL_PREFIX


class TestMessagesMongoDBPooled(v1_1.TestMessagesMongoDBPooled):
    url_prefix = URL_PREFIX


class TestMessagesSqlalchemy(v1_1.TestMessagesSqlalchemy):
    url_prefix = URL_PREFIX


class TestQueueFaultyDriver(v1_1.TestQueueFaultyDriver):
    url_prefix = URL_PREFIX


# TODO(kgriffs): Having to list a separate test for each backend is
# sort of a pain; is there a better way?
class TestQueueLifecycleMongoDB(v1_1.TestQueueLifecycleMongoDB):
    url_prefix = URL_PREFIX


class TestQueueLifecycleSqlalchemy(v1_1.TestQueueLifecycleSqlalchemy):
    url_prefix = URL_PREFIX


class TestPoolsMongoDB(v1_1.TestPoolsMongoDB):
    url_prefix = URL_PREFIX


class TestPoolsSqlalchemy(v1_1.TestPoolsSqlalchemy):
    url_prefix = URL_PREFIX


# --------------------------------------------------------------------------
# v1.1 only
# --------------------------------------------------------------------------

class TestPing(base.V1_1Base):

    config_file = 'wsgi_sqlalchemy.conf'

    def test_get(self):
        # TODO(kgriffs): Make use of setUp for setting the URL prefix
        # so we can just say something like:
        #
        #     response = self.simulate_get('/ping')
        #
        response = self.simulate_get('/v1.1/ping')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

    def test_head(self):
        response = self.simulate_head('/v1.1/ping')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])


class TestHealth(base.V1_1Base):

    config_file = 'wsgi_sqlalchemy.conf'

    def test_get(self):
        response = self.simulate_get('/v1.1/health')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

    def test_head(self):
        response = self.simulate_head('/v1.1/health')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])


@ddt.ddt
class TestMessages(base.V1_1Base):

    config_file = 'wsgi_sqlalchemy.conf'

    def setUp(self):
        super(TestMessages, self).setUp()

        self.queue_path = '/v1.1/queues/test-queue'
        self.messages_path = self.queue_path + '/messages'

        self.project_id = 'e8ba1038'
        self.headers = {'Client-ID': str(uuid.uuid4())}
        self.simulate_put(self.queue_path, self.project_id)

    def tearDown(self):
        self.simulate_delete(self.queue_path, self.project_id)

        super(TestMessages, self).tearDown()

    def _post_messages(self, target, repeat=1):
        doc = jsonutils.dumps([{'body': 239, 'ttl': 300}] * repeat)
        return self.simulate_post(target, self.project_id, body=doc,
                                  headers=self.headers)

    def _get_msg_id(self, headers):
        return self._get_msg_ids(headers)[0]

    def _get_msg_ids(self, headers):
        return headers['Location'].rsplit('=', 1)[-1].split(',')

    @ddt.data(1, 2, 10)
    def test_pop(self, message_count):

        self._post_messages(self.messages_path, repeat=message_count)
        msg_id = self._get_msg_id(self.srmock.headers_dict)
        target = self.messages_path + '/' + msg_id

        self.simulate_get(target, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        query_string = 'pop=' + str(message_count)
        result = self.simulate_delete(self.messages_path, self.project_id,
                                      query_string=query_string)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        result_doc = jsonutils.loads(result[0])

        self.assertEqual(len(result_doc['messages']), message_count)

        self.simulate_get(target, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    @ddt.data('', 'pop=1000000', 'pop=10&ids=1', 'pop=-1')
    def test_pop_invalid(self, query_string):

        self.simulate_delete(self.messages_path, self.project_id,
                             query_string=query_string)
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_pop_empty_queue(self):

        query_string = 'pop=1'
        result = self.simulate_delete(self.messages_path, self.project_id,
                                      query_string=query_string)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        result_doc = jsonutils.loads(result[0])
        self.assertEqual(result_doc['messages'], [])

    def test_pop_single_message(self):

        self._post_messages(self.messages_path, repeat=5)
        msg_id = self._get_msg_id(self.srmock.headers_dict)
        target = self.messages_path + '/' + msg_id

        self.simulate_get(target, self.project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        # Pop Single message from the queue
        query_string = 'pop=1'
        result = self.simulate_delete(self.messages_path, self.project_id,
                                      query_string=query_string)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        # Get messages from the queue & verify message count
        query_string = 'echo=True'
        result = self.simulate_get(self.messages_path, self.project_id,
                                   query_string=query_string,
                                   headers=self.headers)
        result_doc = jsonutils.loads(result[0])
        actual_msg_count = len(result_doc['messages'])
        expected_msg_count = 4
        self.assertEqual(actual_msg_count, expected_msg_count)

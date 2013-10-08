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
#
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import uuid

import ddt
import falcon
import httpretty
import six

import base  # noqa


@ddt.ddt
class QueuesTest(base.TestBase):

    servers = []

    @classmethod
    def setUpClass(cls):
        super(QueuesTest, cls).setUpClass()

    def setUp(self):
        super(QueuesTest, self).setUp()
        self.hosts = ('http://localhost:8000', 'http://localhost:8001')
        self.partition_names = [six.text_type(uuid.uuid1())
                                for _ in self.hosts]
        self.partitions = [u'/v1/partitions/' + name for
                           name in self.partition_names]

        # create two partitions
        for host, uri in zip(self.hosts, self.partitions):
            doc = {'weight': 100, 'hosts': [host]}
            self.simulate_put(uri, body=json.dumps(doc))
            self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def tearDown(self):
        for uri in self.partitions:
            self.simulate_delete(uri)
        super(QueuesTest, self).tearDown()

    @classmethod
    def tearDownClass(cls):
        super(QueuesTest, cls).tearDownClass()

    @ddt.data('get', 'head', 'delete')
    def test_nonexistent_queue_404s_on(self, method):
        getattr(self, 'simulate_' + method)('/v1/queues/no')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    @httpretty.activate
    def _mock_create_queue(self, queue_uri, status):
        for host in self.hosts:
            uri = host + queue_uri
            httpretty.register_uri(httpretty.PUT,
                                   uri, status=status)

        self.simulate_put(queue_uri)
        expect = getattr(falcon, 'HTTP_%s' % status)
        self.assertEqual(self.srmock.status, expect)

    def test_put_queue_creates_catalogue_entry(self):
        queue_uri = '/v1/queues/create'
        catalogue_uri = '/v1/catalogue/create'

        self._mock_create_queue(queue_uri, status=201)

        # is it in the catalogue?
        result = self.simulate_get(catalogue_uri)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        data = json.loads(result[0])
        self.assertEqual(data['name'], 'create')
        self.assertIn(data['partition'], self.partition_names)
        self.assertIn(data['host'], self.hosts)
        self.assertEqual(data['metadata'], {})

    def test_put_queue_leaves_catalogue_alone_on_204(self):
        queue_uri = '/v1/queues/existing'
        catalogue_uri = '/v1/catalogue/existing'

        # NOTE(cpp-cabrera): This test is represents a dysfunctional
        # case: the proxy storage and the queues storage have grown
        # inconsistent. In that case, the queues storage should
        # express that a particular queue was found. If that's the
        # case, (HTTP 204), and no entry was ever created for the
        # proxy storage, then the proxy should correctly return HTTP
        # 404 when accessed through the admin API. This behavior is
        # useful for detecting problems in a deployment, should the
        # proxy storage ever go down at an inopportune moment.
        self._mock_create_queue(queue_uri, status=204)

        # is it in the catalogue?
        self.simulate_get(catalogue_uri)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_put_does_not_duplicate_queues(self):
        queue_uri = '/v1/queues/nodup'

        self._mock_create_queue(queue_uri, status=201)

        for i in range(10):
            self.simulate_put(queue_uri)
            self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def test_list_queues_with_no_queues_204s(self):
        self.simulate_get('/v1/queues')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    # An incomplete test, only for Bug #1234481
    # TODO(zyuan): tearDown the queue creation
    def test_list_queues_with_option_detailed(self):
        self._mock_create_queue('/v1/queues/q1', status=201)
        self._mock_create_queue('/v1/queues/q2', status=201)

        result = self.simulate_get('/v1/queues', query_string="?detailed=True")
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        doc = json.loads(result[0])
        for entry in doc['queues']:
            self.assertIn('metadata', entry)

    @ddt.data(-1, 0, 30)
    def test_list_queues_raises_400_with_invalid_limit(self, limit):
        self.simulate_get('/v1/queues',
                          query_string='limit={0}'.format(limit))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)


@ddt.ddt
class QueuesWithNoPartitionsTest(base.TestBase):

    servers = []

    @classmethod
    def setUpClass(cls):
        super(QueuesWithNoPartitionsTest, cls).setUpClass()

    def setUp(self):
        super(QueuesWithNoPartitionsTest, self).setUp()

    def tearDown(self):
        super(QueuesWithNoPartitionsTest, self).tearDown()

    @classmethod
    def tearDownClass(cls):
        super(QueuesWithNoPartitionsTest, cls).tearDownClass()

    def test_put_raises_500_with_no_partitions_registered(self):
        self.simulate_put('/v1/queues/no')
        self.assertEqual(self.srmock.status, falcon.HTTP_500)

    @ddt.data('get', 'head', 'delete')
    def test_404_with_no_partitions_registered(self, method):
        getattr(self, 'simulate_' + method)('/v1/queues/no')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

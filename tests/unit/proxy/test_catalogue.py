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

import falcon
import httpretty

import base  # noqa


class CatalogueTest(base.TestBase):

    servers = []

    @classmethod
    def setUpClass(cls):
        super(CatalogueTest, cls).setUpClass()

    def setUp(self):
        super(CatalogueTest, self).setUp()
        self.host = 'http://localhost:8000'
        self.partition_name = str(uuid.uuid1())
        self.partition = '/v1/partitions/' + self.partition_name

        # create a partition
        doc = {'weight': 100, 'hosts': [self.host]}
        self.simulate_put(self.partition, body=json.dumps(doc))

    def tearDown(self):
        self.simulate_delete(self.partition)
        super(CatalogueTest, self).tearDown()

    @classmethod
    def tearDownClass(cls):
        super(CatalogueTest, cls).tearDownClass()

    def test_list_empty(self):
        self.simulate_get('/v1/catalogue')
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

    @httpretty.activate
    def test_simple(self):
        queues = ['arakawa', 'bridge']

        self.simulate_get('/v1/catalogue/' + queues[0])
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

        # Create queues
        for name in queues:
            uri = '{0}/v1/queues/{1}'.format(self.host, name)
            httpretty.register_uri(httpretty.PUT, uri, status=201)

            self.simulate_put('/v1/queues/' + name)
            self.assertEqual(self.srmock.status, falcon.HTTP_201)

        for name in queues:
            # mock out forwarding
            uri = '{0}/v1/queues/{1}'.format(self.host, name)
            httpretty.register_uri(httpretty.DELETE, uri, status=204)

            # fetch from the catalogue
            result = self.simulate_get('/v1/catalogue/' + name)
            data = json.loads(result[0])
            self.assertEqual(data['name'], name)
            self.assertEqual(data['partition'], self.partition_name)
            self.assertEqual(data['host'], self.host)
            self.assertEquals(self.srmock.status, falcon.HTTP_200)

            # delete queues, implicitly removing from catalogue
            self.simulate_delete('/v1/queues/' + name)
            self.assertEqual(self.srmock.status, falcon.HTTP_204)

            # ensure entries were removed from catalogue
            self.simulate_get('/v1/catalogue/' + name)
            self.assertEqual(self.srmock.status, falcon.HTTP_404)

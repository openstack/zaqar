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

import copy
import json
import uuid

import ddt
import falcon

import base  # noqa


class PartitionTest(base.TestBase):

    @classmethod
    def setUpClass(cls):
        super(PartitionTest, cls).setUpClass()

    def setUp(self):
        super(PartitionTest, self).setUp()
        self.path = '/v1/partitions'
        self.partition = self.path + '/accel-world'

    def tearDown(self):
        self.simulate_delete(self.partition)
        self.proxy.cache.flush()
        self.proxy.storage.partitions_controller.drop_all()
        super(PartitionTest, self).tearDown()

    @classmethod
    def tearDownClass(cls):
        super(PartitionTest, cls).tearDownClass()

    def test_simple(self):
        # No partition
        self.simulate_get(self.partition)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

        doc = {'hosts': ['url'],
               'weight': 10}

        # Create
        self.simulate_put(self.partition,
                          body=json.dumps(doc))
        self.assertEquals(self.srmock.status, falcon.HTTP_201)

        # Already exist
        doc2 = copy.copy(doc)
        doc2['weight'] = 20

        self.simulate_put(self.partition,
                          body=json.dumps(doc2))
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Get
        result = self.simulate_get(self.partition)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        self.assertEquals(json.loads(result[0]), doc)  # unchanged

        # Delete
        self.simulate_delete(self.partition)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # No longer exist
        self.simulate_get(self.partition)
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_listing(self):
        # Empty
        self.simulate_get(self.path)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # Insert
        for n in range(1, 11):
            doc = {'hosts': map(str, range(n)),
                   'weight': n}

            self.simulate_put(self.partition + str(n),
                              body=json.dumps(doc))
            self.assertEquals(self.srmock.status, falcon.HTTP_201)

        # List
        result = self.simulate_get(self.path)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)
        self.assertEquals(len(json.loads(result[0])), 10)

        # Delete all
        for n in range(1, 11):
            self.simulate_delete(self.partition + str(n))

        # Back to empty
        self.simulate_get(self.path)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

    def test_bad_input(self):
        # Not a JSON
        self.simulate_put('/v1/partitions/avalon', body='{')
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

        # Bad fields
        invalid_nodes = [1, {}, {'hosts': 1}, {'hosts': []}]
        invalid_weights = [{'hosts': ['url']}]
        invalid_weights.append(copy.copy(invalid_weights[0]))
        invalid_weights[1]['weight'] = 3.14

        for doc in invalid_nodes + invalid_weights:
            self.simulate_put('/v1/partitions/avalon',
                              body=json.dumps(doc))
            self.assertEquals(self.srmock.status, falcon.HTTP_400)

    def test_fetch_nonexisting_partition_404s(self):
        self.simulate_get('/v1/partition/no')
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_patch_nonexisting_partition_404s(self):
        doc = {'weight': 1}
        self.simulate_patch('/v1/partition/no', body=json.dumps(doc))
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

    def test_bad_json_on_put_raises_bad_request(self):
        self.simulate_put('/v1/partitions/bad_json', body="")
        self.assertEqual(self.srmock.status, falcon.HTTP_400)


@ddt.ddt
class ExistingPartitionTest(base.TestBase):

    @classmethod
    def setUpClass(cls):
        super(ExistingPartitionTest, cls).setUpClass()

    def setUp(self):
        super(ExistingPartitionTest, self).setUp()
        self.weight = 100
        self.hosts = ['a']
        self.name = str(uuid.uuid1())
        self.partition_uri = '/v1/partitions/' + self.name
        doc = {'weight': self.weight, 'hosts': self.hosts}
        self.simulate_put(self.partition_uri, body=json.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def tearDown(self):
        self.simulate_delete(self.partition_uri)
        super(ExistingPartitionTest, self).tearDown()

    @classmethod
    def tearDownClass(cls):
        super(ExistingPartitionTest, cls).tearDownClass()

    def test_put_on_existing_partition_204s(self):
        self.simulate_put(self.partition_uri, body="")
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def test_patch_weight(self):
        doc = {'weight': self.weight + 1}
        self.simulate_patch(self.partition_uri,
                            body=json.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        result = self.simulate_get(self.partition_uri)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        doc = json.loads(result[0])
        self.assertEqual(doc['weight'], self.weight + 1)

    def test_patch_hosts(self):
        doc = {'hosts': self.hosts + ['b']}
        self.simulate_patch(self.partition_uri,
                            body=json.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        result = self.simulate_get(self.partition_uri)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        doc = json.loads(result[0])
        self.assertEqual(doc['hosts'], self.hosts + ['b'])

    def test_partition_route_respects_allowed(self):
        for method in ('head', 'post'):
            getattr(self, 'simulate_' + method)(self.partition_uri)
            self.assertEqual(self.srmock.status, falcon.HTTP_405)

    def test_bad_json_on_patch_raises_bad_request(self):
        self.simulate_patch(self.partition_uri, body="{")
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_patch_fails_validation_when_missing_hosts_and_weight(self):
        doc = {'winning': 1}
        self.simulate_patch(self.partition_uri, body=json.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-10, -1, 0, 'a', 2**64 + 1)
    def test_patch_fails_validation_with_invalid_weight(self, weight):
        doc = {'weight': weight}
        self.simulate_patch(self.partition_uri, body=json.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data([], 'localhost', 1)
    def test_patch_fails_validation_with_invalid_hosts(self, hosts):
        doc = {'hosts': hosts}
        self.simulate_patch(self.partition_uri, body=json.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

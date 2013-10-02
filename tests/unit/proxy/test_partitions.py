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

import falcon

import base  # noqa


class PartitionTest(base.TestBase):

    def setUp(self):
        super(PartitionTest, self).setUp()
        self.path = '/v1/partitions'
        self.partition = self.path + '/accel-world'

    def tearDown(self):
        self.simulate_delete(self.partition)
        self.proxy.cache.flush()
        self.proxy.storage.partitions_controller.drop_all()
        super(PartitionTest, self).tearDown()

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

    def test_reserved_partition(self):
        doc = {'hosts': ['url'],
               'weight': 10}

        self.simulate_put('/v1/partitions/__cplusplus',
                          body=json.dumps(doc))
        self.assertEquals(self.srmock.status, falcon.HTTP_400)

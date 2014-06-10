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
import ddt

from marconi.tests.functional import base
from marconi.tests.functional import helpers


@ddt.ddt
class TestShards(base.V1_1FunctionalTestBase):

    server_class = base.MarconiServer

    def setUp(self):
        super(TestShards, self).setUp()

        self.shard_url = ("{url}/{version}/shards".format(
            url=self.cfg.marconi.url,
            version="v1.1"
        ))
        self.cfg.marconi.version = "v1.1"

        self.skipTest("NOT IMPLEMENTED")

        self.headers = helpers.create_marconi_headers(self.cfg)
        self.client.headers = self.headers

        self.client.set_base_url(self.shard_url)

    def tearDown(self):
        super(TestShards, self).tearDown()

    @ddt.data(
        {
            'name': "newshard",
            'weight': 10,
            'uri': "mongodb://127.0.0.1:27017"
        }
    )
    def test_insert_shard(self, params):
        """Test the registering of one shard."""
        doc = helpers.create_shard_body(
            weight=params.get('weight', 10),
            uri=params.get('uri', "mongodb://127.0.0.1:27017")
        )

        shard_name = params.get('name', "newshard")
        self.addCleanup(self.client.delete, url='/'+shard_name)

        result = self.client.put('/'+shard_name, data=doc)
        self.assertEqual(result.status_code, 201)

        # Test existence
        result = self.client.get('/'+shard_name)
        self.assertEqual(result.status_code, 200)

    @ddt.data(
        {
            'name': "newshard",
            'weight': 10,
            'uri': "mongodb://127.0.0.1:27017"
        }
    )
    def test_shard_details(self, params):
        """Get the details of a shard. Assert the respective schema."""
        doc = helpers.create_shard_body(
            weight=params.get('weight', 10),
            uri=params.get('uri', "mongodb://127.0.0.1:27017")
        )

        shard_name = params.get('name', "newshard")
        self.addCleanup(self.client.delete, url='/'+shard_name)
        result = self.client.put('/'+shard_name, data=doc)
        self.assertEqual(result.status_code, 201)

        # Test existence
        result = self.client.get('/'+shard_name+'?detailed=true')
        self.assertEqual(result.status_code, 200)
        self.assertSchema(result.json(), 'shard-detail')

    @ddt.data(
        {
            'name': "newshard",
            'weight': 10,
            'uri': "mongodb://127.0.0.1:27017"
        }
    )
    def test_delete_shard(self, params):
        """Create a shard, then delete it.

        Make sure operation is successful.
        """

        # Create the shard
        doc = helpers.create_shard_body(
            weight=params.get('weight', 10),
            uri=params.get('uri', "mongodb://127.0.0.1:27017")
        )

        shard_name = params.get('name', "newshard")
        result = self.client.put('/'+shard_name, data=doc)
        self.assertEqual(result.status_code, 201)

        # Make sure it exists
        result = self.client.get('/'+shard_name)
        self.assertEqual(result.status_code, 200)

        # Delete it
        result = self.client.delete('/'+shard_name)
        self.assertEqual(result.status_code, 204)

    @ddt.data(
        {
            'name': "newshard",
            'weight': 10,
            'uri': "mongodb://127.0.0.1:27017"
        }
    )
    def test_list_shards(self, params):
        """Add a shard. Get the list of all the shards.

        Assert respective schema
        """
        doc = helpers.create_shard_body(
            weight=params.get('weight', 10),
            uri=params.get('uri', "mongodb://127.0.0.1:27017")
        )
        shard_name = params.get('name', "newshard")
        self.addCleanup(self.client.delete, url='/'+shard_name)
        result = self.client.put('/'+shard_name, data=doc)
        self.assertEqual(result.status_code, 201)

        result = self.client.get()
        self.assertEqual(result.status_code, 200)
        self.assertSchema(result.json(), 'shard-list')

    @ddt.data(
        {
            'name': "newshard",
            'weight': 10,
            'uri': "mongodb://127.0.0.1:27017"
        }
    )
    def test_patch_shard(self, params):
        """Create a shard. Issue a patch command,

        make sure command was successful. Check details to be sure.
        """

        doc = helpers.create_shard_body(
            weight=params.get('weight', 10),
            uri=params.get('uri', "mongodb://127.0.0.1:27017")
        )
        shard_name = params.get('name', "newshard")
        self.addCleanup(self.client.delete, url='/'+shard_name)
        result = self.client.put('/'+shard_name, data=doc)
        self.assertEqual(result.status_code, 201)
        # Update that shard

        patchdoc = helpers.create_shard_body(
            weight=5,
            uri="mongodb://127.0.0.1:27017"
        )
        result = self.client.patch('/'+shard_name, data=patchdoc)
        self.assertEqual(result.status_code, 200)

        # Get the shard, check update#
        result = self.client.get('/'+shard_name)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["weight"], 5)

    @ddt.data(
        {
            'name': "newshard",
            'weight': 10,
            'uri': "mongodb://127.0.0.1:27017"
        }
    )
    def test_patch_shard_bad_data(self, params):
        """Issue a patch command without a body. Assert 400."""
        # create a shard
        doc = helpers.create_shard_body(
            weight=params.get('weight', 10),
            uri=params.get('uri', "mongodb://127.0.0.1:27017")
        )
        shard_name = params.get('name', "newshard")
        self.addCleanup(self.client.delete, url='/'+shard_name)
        result = self.client.put('/'+shard_name, data=doc)
        self.assertEqual(result.status_code, 201)

        # Update shard with bad post data. Ensure 400
        result = self.client.patch('/'+shard_name)
        self.assertEqual(result.status_code, 400)

    @ddt.data(
        {
            'name': "newshard",
            'weight': 10,
            'uri': "mongodb://127.0.0.1:27017"
        }
    )
    def test_patch_shard_non_exist(self, params):
        """Issue patch command to shard that doesn't exist. Assert 404."""
        doc = helpers.create_shard_body(
            weight=5,
            uri=params.get('uri', "mongodb://127.0.0.1:27018")
        )
        result = self.client.patch('/nonexistshard', data=doc)
        self.assertEqual(result.status_code, 404)

    @ddt.data(
        {'name': u'\u6c49\u5b57\u6f22\u5b57'},
        {'name': 'i'*65},
        {'weight': -1}
    )
    def test_insert_shard_bad_data(self, params):
        """Create shards with invalid names and weights. Assert 400."""
        doc = helpers.create_shard_body(
            weight=params.get('weight', 10),
            uri=params.get('uri', "mongodb://127.0.0.1:27017")
        )
        shard_name = params.get('name', "newshard")
        self.addCleanup(self.client.delete, url='/'+shard_name)
        result = self.client.put('/'+shard_name, data=doc)
        self.assertEqual(result.status_code, 400)

    def test_delete_shard_non_exist(self):
        """Delete a shard that doesn't exist. Assert 404."""
        result = self.client.delete('/nonexistshard')
        self.assertEqual(result.status_code, 204)

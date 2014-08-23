# Copyright (c) 2014 Catalyst IT Ltd
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

from zaqar.tests.functional import base
from zaqar.tests.functional import helpers


@ddt.ddt
class TestHealth(base.V1_1FunctionalTestBase):

    server_class = base.ZaqarAdminServer

    def setUp(self):
        super(TestHealth, self).setUp()
        self.base_url = ("{url}/{version}".format(
            url=self.cfg.zaqar.url,
            version="v1.1"
        ))
        self.cfg.zaqar.version = "v1.1"
        self.client.set_base_url(self.base_url)

    @ddt.data(
        {
            'name': "pool_1",
            'weight': 10,
            'uri': "sqlite:///:memory:"
        }
    )
    def test_health_with_pool(self, params):
        # FIXME(flwang): Please use mongodb after the sqlalchemy is disabled
        # as pool node and the mongodb is working on gate successfully.
        doc = helpers.create_pool_body(
            weight=params.get('weight', 10),
            uri=params.get('uri', "sqlite:///:memory:")
        )

        pool_name = params.get('name', "pool_1")
        self.addCleanup(self.client.delete, url='/pools/' + pool_name)

        result = self.client.put('/pools/' + pool_name, data=doc)
        self.assertEqual(result.status_code, 201)

        queue_name = 'fake_queue'
        self.addCleanup(self.client.delete, url='/queues/' + queue_name)
        result = self.client.put('/queues/' + queue_name)
        self.assertEqual(result.status_code, 201)

        sample_messages = {'messages': [
            {'body': 239, 'ttl': 999},
            {'body': {'key': 'value'}, 'ttl': 888}
        ]}

        result = self.client.post('/queues/%s/messages' % queue_name,
                                  data=sample_messages)
        self.assertEqual(result.status_code, 201)

        claim_metadata = {'ttl': 100, 'grace': 300}

        result = self.client.post('/queues/%s/claims' % queue_name,
                                  data=claim_metadata)
        self.assertEqual(result.status_code, 201)

        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        health = response.json()

        self.assertEqual(health['catalog_reachable'], True)
        self.assertEqual(health[pool_name]['storage_reachable'], True)
        op_status = health[pool_name]['operation_status']
        for op in op_status.keys():
                self.assertTrue(op_status[op]['succeeded'])

        message_volume = health[pool_name]['message_volume']
        self.assertEqual(message_volume['claimed'], 2)
        self.assertEqual(message_volume['free'], 0)
        self.assertEqual(message_volume['total'], 2)

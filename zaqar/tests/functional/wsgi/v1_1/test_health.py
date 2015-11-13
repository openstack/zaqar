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

from zaqar.tests.functional import base
from zaqar.tests.functional import helpers


class TestHealth(base.V1_1FunctionalTestBase):

    server_class = base.ZaqarAdminServer
    config_file = 'wsgi_mongodb_pooled.conf'

    def setUp(self):
        super(TestHealth, self).setUp()
        self.base_url = ("{url}/{version}".format(
            url=self.cfg.zaqar.url,
            version="v1.1"
        ))
        self.cfg.zaqar.version = "v1.1"

        self.headers = helpers.create_zaqar_headers(self.cfg)
        self.client.headers = self.headers

        self.client.set_base_url(self.base_url)

    def test_health_with_pool(self):
        # FIXME(flwang): Please use mongodb after the sqlalchemy is disabled
        # as pool node and the mongodb is working on gate successfully.
        doc = helpers.create_pool_body(
            weight=10,
            uri=self.mconf['drivers:management_store:mongodb'].uri,
            options=dict(database='zaqar_test_pooled_1')
        )

        pool_name = "pool_1"

        result = self.client.put('/pools/' + pool_name, data=doc)
        self.assertEqual(201, result.status_code)

        queue_name = 'fake_queue'
        result = self.client.put('/queues/' + queue_name)
        self.assertEqual(201, result.status_code)

        sample_messages = {'messages': [
            {'body': 239, 'ttl': 999},
            {'body': {'key': 'value'}, 'ttl': 888}
        ]}

        result = self.client.post('/queues/%s/messages' % queue_name,
                                  data=sample_messages)
        self.assertEqual(201, result.status_code)

        claim_metadata = {'ttl': 100, 'grace': 300}

        result = self.client.post('/queues/%s/claims' % queue_name,
                                  data=claim_metadata)
        self.assertEqual(201, result.status_code)

        response = self.client.get('/health')
        self.assertEqual(200, response.status_code)
        health = response.json()

        self.assertTrue(health['catalog_reachable'])
        self.assertTrue(health[pool_name]['storage_reachable'])
        op_status = health[pool_name]['operation_status']
        for op in op_status.keys():
            self.assertTrue(op_status[op]['succeeded'])

        message_volume = health[pool_name]['message_volume']
        self.assertEqual(2, message_volume['claimed'])
        self.assertEqual(0, message_volume['free'])
        self.assertEqual(2, message_volume['total'])

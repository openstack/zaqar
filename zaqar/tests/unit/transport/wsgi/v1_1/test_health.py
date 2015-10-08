# Copyright 2014 Catalyst IT Ltd
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
import falcon
import mock
from oslo_serialization import jsonutils

from zaqar.storage import errors
import zaqar.storage.mongodb as mongo
from zaqar import tests as testing
from zaqar.tests.unit.transport.wsgi import base


@ddt.ddt
class TestHealthMongoDB(base.V1_1Base):

    config_file = 'wsgi_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestHealthMongoDB, self).setUp()

    def test_basic(self):
        path = self.url_prefix + '/health'
        body = self.simulate_get(path)
        health = jsonutils.loads(body[0])
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertTrue(health['storage_reachable'])
        self.assertIsNotNone(health['message_volume'])
        for op in health['operation_status']:
            self.assertTrue(health['operation_status'][op]['succeeded'])

    @mock.patch.object(mongo.driver.DataDriver, '_health')
    def test_message_volume(self, mock_driver_get):
        def _health():
            KPI = {}
            KPI['message_volume'] = {'free': 1, 'claimed': 2, 'total': 3}
            return KPI

        mock_driver_get.side_effect = _health

        path = self.url_prefix + '/health'
        body = self.simulate_get(path)
        health = jsonutils.loads(body[0])
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        message_volume = health['message_volume']
        self.assertEqual(1, message_volume['free'])
        self.assertEqual(2, message_volume['claimed'])
        self.assertEqual(3, message_volume['total'])

    @mock.patch.object(mongo.messages.MessageController, 'delete')
    def test_operation_status(self, mock_messages_delete):
        mock_messages_delete.side_effect = errors.NotPermitted()

        path = self.url_prefix + '/health'
        body = self.simulate_get(path)
        health = jsonutils.loads(body[0])
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        op_status = health['operation_status']
        for op in op_status.keys():
            if op == 'delete_messages':
                self.assertFalse(op_status[op]['succeeded'])
                self.assertIsNotNone(op_status[op]['ref'])
            else:
                self.assertTrue(op_status[op]['succeeded'])


class TestHealthFaultyDriver(base.V1_1BaseFaulty):

    config_file = 'wsgi_faulty.conf'

    def test_simple(self):
        path = self.url_prefix + '/health'
        self.simulate_get(path)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

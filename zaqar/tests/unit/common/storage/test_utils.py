# Copyright (c) 2014 Rackspace Hosting, Inc.
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

from zaqar.common import configs
from zaqar.storage import utils
from zaqar import tests as testing


@ddt.ddt
class TestUtils(testing.TestBase):

    def setUp(self):
        super(TestUtils, self).setUp()
        self.conf.register_opts(configs._GENERAL_OPTIONS)

    @testing.requires_mongodb
    def test_can_connect_succeeds_if_good_uri_mongo(self):
        self.config(unreliable=True)
        self.assertTrue(utils.can_connect(self.mongodb_url,
                                          conf=self.conf))

    @testing.requires_redis
    def test_can_connect_succeeds_if_good_uri_redis(self):
        self.assertTrue(utils.can_connect('redis://localhost',
                                          conf=self.conf))
        self.assertTrue(utils.can_connect('redis://localhost:6379',
                                          conf=self.conf))

    def test_can_connect_fails_if_bad_uri_missing_schema(self):
        self.assertFalse(utils.can_connect('localhost:27017',
                                           conf=self.conf))

    @testing.requires_mongodb
    def test_can_connect_fails_if_bad_uri_mongodb(self):
        self.config(unreliable=True)

        uri = 'mongodb://localhost:8080?connectTimeoutMS=100'
        self.assertFalse(utils.can_connect(uri, conf=self.conf))

        uri = 'mongodb://example.com:27017?connectTimeoutMS=100'
        self.assertFalse(utils.can_connect(uri, conf=self.conf))

    @testing.requires_redis
    def test_can_connect_fails_if_bad_uri_redis(self):
        self.assertFalse(utils.can_connect('redis://localhost:8080',
                                           conf=self.conf))
        self.assertFalse(utils.can_connect('redis://example.com:6379',
                                           conf=self.conf))

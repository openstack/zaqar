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

from marconi.queues.storage import utils
from marconi import tests as testing


@ddt.ddt
class TestUtils(testing.TestBase):

    @testing.requires_mongodb
    def test_can_connect_suceeds_if_good_uri_mongo(self):
        self.assertTrue(utils.can_connect('mongodb://localhost:27017'))

    def test_can_connect_suceeds_if_good_uri_sqlite(self):
        self.assertTrue(utils.can_connect('sqlite://:memory:'))

    @ddt.data(
        'mongodb://localhost:27018',  # wrong port
        'localhost:27017',  # missing scheme
        'redis://localhost:6379'  # not supported with default install
    )
    @testing.requires_mongodb
    def test_can_connect_fails_if_bad_uri(self, uri):
        self.assertFalse(utils.can_connect(uri))

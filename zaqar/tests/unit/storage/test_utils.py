# Copyright (c) 2017 Catalyst IT Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import mock

from zaqar.storage import utils
from zaqar import tests as testing


class StorageUtilsTest(testing.TestBase):
    config_file = 'wsgi_swift.conf'

    def test_can_connect(self):
        swift_uri = "swift://zaqar:password@/service"
        is_alive_path = 'zaqar.storage.swift.driver.DataDriver.is_alive'
        with mock.patch(is_alive_path) as is_alive:
            is_alive.return_value = True
            self.assertTrue(utils.can_connect(swift_uri, self.conf))

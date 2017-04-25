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
from zaqar.common import cache as oslo_cache
from zaqar.storage import mongodb
from zaqar.storage.swift import controllers
from zaqar.storage.swift import driver
from zaqar import tests as testing
from zaqar.tests.unit.storage import base


@testing.requires_swift
class SwiftMessagesTest(base.MessageControllerTest):
    driver_class = driver.DataDriver
    config_file = 'wsgi_swift.conf'
    controller_class = controllers.MessageController
    control_driver_class = mongodb.ControlDriver
    gc_interval = 1


@testing.requires_swift
class SwiftClaimsTest(base.ClaimControllerTest):
    driver_class = driver.DataDriver
    config_file = 'wsgi_swift.conf'
    controller_class = controllers.ClaimController
    control_driver_class = mongodb.ControlDriver


@testing.requires_swift
class SwiftSubscriptionsTest(base.SubscriptionControllerTest):
    driver_class = driver.DataDriver
    config_file = 'wsgi_swift.conf'
    controller_class = controllers.SubscriptionController
    control_driver_class = mongodb.ControlDriver


@testing.requires_swift
class SwiftDriverTest(testing.TestBase):
    config_file = 'wsgi_swift.conf'

    def test_is_alive(self):
        oslo_cache.register_config(self.conf)
        cache = oslo_cache.get_cache(self.conf)
        swift_driver = driver.DataDriver(self.conf, cache,
                                         mongodb.ControlDriver
                                         (self.conf, cache))

        self.assertTrue(swift_driver.is_alive())

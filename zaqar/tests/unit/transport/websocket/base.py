# Copyright (c) 2015 Red Hat, Inc.
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

from oslo_serialization import jsonutils

from zaqar import bootstrap
from zaqar.conf import default
from zaqar.conf import drivers_transport_websocket
from zaqar.conf import transport
from zaqar import tests as testing


class TestBase(testing.TestBase):

    config_file = None

    def setUp(self):
        super().setUp()

        if not self.config_file:
            self.skipTest("No config specified")

        self.conf.register_opts(default.ALL_OPTS)
        self.conf.register_opts(transport.ALL_OPTS,
                                group=transport.GROUP_NAME)
        self.transport_cfg = self.conf[transport.GROUP_NAME]

        self.conf.register_opts(drivers_transport_websocket.ALL_OPTS,
                                group=drivers_transport_websocket.GROUP_NAME)
        self.ws_cfg = self.conf[drivers_transport_websocket.GROUP_NAME]

        self.conf.unreliable = True
        self.conf.admin_mode = True
        self.boot = bootstrap.Bootstrap(self.conf)
        self.addCleanup(self.boot.storage.close)
        self.addCleanup(self.boot.control.close)

        self.transport = self.boot.transport
        self.api = self.boot.api

    def tearDown(self):
        if self.conf.pooling:
            self.boot.control.pools_controller.drop_all()
            self.boot.control.catalogue_controller.drop_all()
        super().tearDown()


class TestBaseFaulty(TestBase):
    """This test ensures we aren't letting any exceptions go unhandled."""


class V1_1Base(TestBase):
    """Base class for V1.1 API Tests.

    Should contain methods specific to V1.1 of the API
    """

    def _empty_message_list(self, body):
        self.assertEqual([], jsonutils.loads(body[0])['messages'])


class V1_1BaseFaulty(TestBaseFaulty):
    """Base class for V1.1 API Faulty Tests.

    Should contain methods specific to V1.1 exception testing
    """
    pass


class V2Base(V1_1Base):
    """Base class for V2 API Tests.

    Should contain methods specific to V2 of the API
    """


class V2BaseFaulty(V1_1BaseFaulty):
    """Base class for V2 API Faulty Tests.

    Should contain methods specific to V2 exception testing
    """

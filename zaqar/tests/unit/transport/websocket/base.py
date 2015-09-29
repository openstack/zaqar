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
from zaqar.common import configs
from zaqar import tests as testing
from zaqar.transport import validation
from zaqar.transport.websocket import driver


class TestBase(testing.TestBase):

    config_file = None

    def setUp(self):
        super(TestBase, self).setUp()

        if not self.config_file:
            self.skipTest("No config specified")

        self.conf.register_opts(configs._GENERAL_OPTIONS)
        self.conf.register_opts(validation._TRANSPORT_LIMITS_OPTIONS,
                                group=validation._TRANSPORT_LIMITS_GROUP)
        self.transport_cfg = self.conf[validation._TRANSPORT_LIMITS_GROUP]

        self.conf.register_opts(driver._WS_OPTIONS,
                                group=driver._WS_GROUP)
        self.ws_cfg = self.conf[driver._WS_GROUP]

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
        super(TestBase, self).tearDown()


class TestBaseFaulty(TestBase):
    """This test ensures we aren't letting any exceptions go unhandled."""


class V1Base(TestBase):
    """Base class for V1 API Tests.

    Should contain methods specific to V1 of the API
    """
    pass


class V1BaseFaulty(TestBaseFaulty):
    """Base class for V1 API Faulty Tests.

    Should contain methods specific to V1 exception testing
    """
    pass


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

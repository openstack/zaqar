# Copyright (c) 2013 Rackspace, Inc.
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
#
# See the License for the specific language governing permissions and
# limitations under the License.

from falcon import testing as ftest

from marconi.common.transport import version
from marconi.proxy.admin import bootstrap as admin
from marconi.proxy.transport.wsgi import queues
from marconi.proxy.utils import round_robin
from tests.unit.queues.transport.wsgi import base


class TestBase(base.TestBase):

    config_filename = "wsgi_proxy_memory.conf"

    @classmethod
    def setUpClass(cls):
        super(TestBase, cls).setUpClass()
        TestBase._proxy = admin.Bootstrap()

        TestBase._app = TestBase._proxy.transport.app
        partitions_controller = TestBase._proxy.storage.partitions_controller
        catalogue_controller = TestBase._proxy.storage.catalogue_controller
        cache = TestBase._proxy.cache
        selector = round_robin.Selector()

        # NOTE(cpp-cabrera): allow for queue creation: needed for
        # catalogue tests
        TestBase._app.add_route(version.path() + '/queues/{queue}',
                                queues.Resource(partitions_controller,
                                                catalogue_controller,
                                                cache, selector))

        # NOTE(cpp-cabrera): allow for queue listing
        # TODO(cpp-cabrera): move this out into proxy:public test base
        TestBase._app.add_route(version.path() + '/queues',
                                queues.Listing(catalogue_controller))

    def setUp(self):
        super(TestBase, self).setUp()
        self.app = TestBase._app
        self.proxy = TestBase._proxy
        self.srmock = ftest.StartResponseMock()

    @classmethod
    def tearDownClass(cls):
        super(TestBase, cls).tearDownClass()

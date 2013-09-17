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

import os

from falcon import testing as ftest

from marconi.proxy import app
from tests.unit.transport.wsgi import base


class TestBase(base.TestBase):

    def setUp(self):
        if not os.environ.get('REDIS_TEST_LIVE'):
            self.skipTest('No Redis instance running')

        super(base.TestBase, self).setUp()

        self.app = app.app
        self.srmock = ftest.StartResponseMock()

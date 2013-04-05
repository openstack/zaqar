# Copyright (c) 2013 Red Hat, Inc.
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

import multiprocessing
import signal

import marconi
from marconi.tests import util
from marconi.transport.wsgi import app


class TestApplication(util.TestBase):

    def setUp(self):
        super(TestApplication, self).setUp()

        conf_file = self.conf_path('wsgi_sqlite.conf')
        boot = marconi.Bootstrap(conf_file)

        self.app = app.Application(boot.transport.app)

    def test_run(self):
        server = multiprocessing.Process(target=self.app.run)
        server.start()
        self.assertTrue(server.is_alive())
        server.terminate()
        server.join()
        self.assertEquals(server.exitcode, -signal.SIGTERM)

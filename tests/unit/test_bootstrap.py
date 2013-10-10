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
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo.config import cfg

from marconi.common import exceptions
import marconi.queues
from marconi.queues.storage import pipeline
from marconi.queues.storage import sqlite
from marconi.queues.transport import wsgi
from marconi.tests import base


class TestBootstrap(base.TestBase):

    def test_config_missing(self):
        self.assertRaises(cfg.ConfigFilesNotFoundError, marconi.Bootstrap, '')

    def test_storage_invalid(self):
        conf_file = 'etc/drivers_storage_invalid.conf'
        bootstrap = marconi.Bootstrap(conf_file)
        self.assertRaises(exceptions.InvalidDriver,
                          lambda: bootstrap.storage)

    def test_storage_sqlite(self):
        conf_file = 'etc/wsgi_sqlite.conf'
        bootstrap = marconi.Bootstrap(conf_file)
        self.assertIsInstance(bootstrap.storage, pipeline.Driver)
        self.assertIsInstance(bootstrap.storage._storage, sqlite.Driver)

    def test_transport_invalid(self):
        conf_file = 'etc/drivers_transport_invalid.conf'
        bootstrap = marconi.Bootstrap(conf_file)
        self.assertRaises(exceptions.InvalidDriver,
                          lambda: bootstrap.transport)

    def test_transport_wsgi(self):
        bootstrap = marconi.Bootstrap('etc/wsgi_sqlite.conf')

        self.assertIsInstance(bootstrap.transport, wsgi.Driver)

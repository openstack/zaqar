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

from oslo.config import cfg

from marconi.queues.storage import sharding
from marconi.queues.storage import sqlite
from marconi.tests import base


class TestShardCatalog(base.TestBase):

    def test_lookup(self):
        # TODO(kgriffs): SHARDING - configure sharding to use an in-memory
        # backend store, and register the queues we are going to look up.
        conf_file = 'etc/wsgi_sqlite_sharded.conf'

        conf = cfg.ConfigOpts()
        conf(args=[], default_config_files=[conf_file])

        lookup = sharding.Catalog(conf).lookup

        storage = lookup('q1', '123456')
        self.assertIsInstance(storage, sqlite.DataDriver)

        storage = lookup('q2', '123456')
        self.assertIsInstance(storage, sqlite.DataDriver)

        storage = lookup('g1', None)
        self.assertIsInstance(storage, sqlite.DataDriver)

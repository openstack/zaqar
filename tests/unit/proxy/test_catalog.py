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

import json
import random

import falcon

from marconi.queues import bootstrap

import base  # noqa


class CatalogTest(base.TestBase):

    servers = []

    @classmethod
    def setUpClass(cls):
        ports = range(8900, 8903)
        app = bootstrap.Bootstrap().transport.app
        cls.servers = [base.make_app_daemon('localhost', pt, app)
                       for pt in ports]
        # TODO(cpp-cabrera): allow trailing slash
        cls.urls = ['http://127.0.0.1:%d' % pt for pt in ports]

    @classmethod
    def tearDownClass(cls):
        for p in cls.servers:
            p.terminate()

    def tearDown(self):
        for server in self.servers:
            self.simulate_delete('/v1/partitions/' + server.name)

        # TODO(zyuan): use a storage API call to cleanup the catalogs
        super(CatalogTest, self).tearDown()

    def __add_partitions(self):
        for name, url, weight in zip(
                [server.name for server in self.servers],
                self.urls,
                random.sample(xrange(100), len(self.urls))):
            doc = {'hosts': [url], 'weight': weight}
            self.simulate_put('/v1/partitions/' + name,
                              body=json.dumps(doc))
            self.assertEquals(self.srmock.status, falcon.HTTP_201)

    def test_simple(self):
        path = '/v1/catalogue'
        queue_names = ['arakawa', 'bridge']

        # No catalog created yet
        self.simulate_get(path)
        self.assertEquals(self.srmock.status, falcon.HTTP_204)

        # TODO(cpp-cabrera): what if there is no partition?

        self.__add_partitions()

        # Queue is not touched
        result = self.simulate_get('/v1/catalogue/' + queue_names[0])
        self.assertEquals(self.srmock.status, falcon.HTTP_404)

        # Create queues (and implicitly, catalog)
        for name in queue_names:
            self.simulate_put('/v1/queues/' + name)
            self.assertEquals(self.srmock.status, falcon.HTTP_201)

        result = self.simulate_get(path)
        self.assertEquals(self.srmock.status, falcon.HTTP_200)

        doc = json.loads(result[0])

        for name in queue_names:
            self.assertIn(name, doc)
            self.assertIn(doc[name]['host'], self.urls)

            result = self.simulate_get('/v1/catalogue/' + name)
            self.assertEquals(self.srmock.status, falcon.HTTP_200)

            each_doc = json.loads(result[0])
            self.assertEquals(each_doc, doc[name])

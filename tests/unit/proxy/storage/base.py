# Copyright (c) 2013 Rackspace Hosting, Inc.
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
import uuid

import six

from marconi.proxy import storage
from marconi.proxy.storage import exceptions
from marconi import tests as testing
from marconi.tests import helpers


class ControllerBaseTest(testing.TestBase):
    project = 'project'
    driver_class = None
    controller_class = None
    controller_base_class = None

    def setUp(self):
        super(ControllerBaseTest, self).setUp()

        if not self.driver_class:
            self.skipTest('No driver class specified')

        if not issubclass(self.controller_class, self.controller_base_class):
            self.skipTest('{0} is not an instance of {1}. '
                          'Tests not supported'.format(
                          self.controller_class, self.controller_base_class))

        self.driver = self.driver_class()
        self.controller = self.controller_class(self.driver)


class PartitionsControllerTest(ControllerBaseTest):
    controller_base_class = storage.PartitionsBase

    def setUp(self):
        super(PartitionsControllerTest, self).setUp()
        self.controller = self.driver.partitions_controller
        self.name = six.text_type(uuid.uuid1())

    def tearDown(self):
        super(PartitionsControllerTest, self).tearDown()

    def _check_structure(self, partition):
        self.assertIn('name', partition)
        self.assertIsInstance(partition['name'], six.text_type)
        self.assertIn('hosts', partition)
        self.assertIsInstance(partition['hosts'], list)
        self.assertIsInstance(partition['hosts'][0], six.text_type)
        self.assertIn('weight', partition)
        self.assertIsInstance(partition['weight'], int)

    def _check_values(self, partition, xname, xweight, xhosts):
        self.assertEqual(partition['name'], xname)
        self.assertEqual(partition['weight'], xweight)
        self.assertEqual(partition['hosts'], xhosts)

    def test_partition_life_cycle(self):
        # check listing is initially empty
        for p in self.controller.list():
            self.fail('There should be no partitions at this time')

        # create a listing, check its length
        with helpers.partitions(self.controller, 10):
            ps = list(self.controller.list())
            self.assertEqual(len(ps), 10)

        # create, check existence, delete
        with helpers.partition(self.controller, self.name, 1, ['a']):
            self.assertTrue(self.controller.exists(self.name))

        # verify it no longer exists
        self.assertFalse(self.controller.exists(self.name))

        # verify it isn't listable
        self.assertEqual(len(list(self.controller.list())), 0)

    def test_list(self):
        with helpers.partitions(self.controller, 10) as expect:
            values = zip(self.controller.list(), expect)
            for p, x in values:
                n, w, h = x
                self._check_structure(p)
                self._check_values(p, xname=n, xweight=w, xhosts=h)

    def test_get(self):
        name = self.name
        with helpers.partition(self.controller, name, 10, ['a']) as expect:
            p = self.controller.get(name)
            n, w, h = expect
            self._check_values(p, xname=n, xweight=w, xhosts=h)

    def test_get_nonexistent_throws(self):
        self.assertRaises(exceptions.PartitionNotFound,
                          self.controller.get, ('not_found'))

    def test_exists(self):
        name = self.name
        with helpers.partition(self.controller, name, 10, ['a']):
            self.assertTrue(self.controller.exists(name))

    def test_create_overwrites(self):
        name = self.name
        with helpers.partition(self.controller, name, 1, ['a']):
            with helpers.partition(self.controller, name, 2, ['b']) as p2:
                fetched = self.controller.get(name)
                n, w, h = p2
                self._check_values(fetched, xname=n, xweight=w, xhosts=h)


class CatalogueControllerTest(ControllerBaseTest):
    controller_base_class = storage.CatalogueBase

    def setUp(self):
        super(CatalogueControllerTest, self).setUp()
        self.controller = self.driver.catalogue_controller
        self.queue = six.text_type(uuid.uuid1())
        self.project = six.text_type(uuid.uuid1())

    def tearDown(self):
        super(CatalogueControllerTest, self).tearDown()

    def _check_structure(self, entry):
        self.assertIn('name', entry)
        self.assertIn('metadata', entry)
        self.assertIn('partition', entry)
        self.assertIn('host', entry)
        self.assertIsInstance(entry['name'], six.text_type)
        self.assertIsInstance(entry['metadata'], dict)
        self.assertIsInstance(entry['partition'], six.text_type)
        self.assertIsInstance(entry['host'], six.text_type)

    def _check_value(self, entry, xname, xmeta, xpartition, xhost):
        self.assertEqual(entry['name'], xname)
        self.assertEqual(entry['metadata'], xmeta)
        self.assertEqual(entry['partition'], xpartition)
        self.assertEqual(entry['host'], xhost)

    def test_catalogue_entry_life_cycle(self):
        queue = self.queue
        project = self.project

        # check listing is initially empty
        for p in self.controller.list(project):
            self.fail('There should be no entries at this time')

        # create a listing, check its length
        with helpers.entries(self.controller, 10):
            xs = list(self.controller.list(u'_'))
            self.assertEqual(len(xs), 10)

        # create, check existence, delete
        with helpers.entry(self.controller, project, queue, u'a', u'a'):
            self.assertTrue(self.controller.exists(project, queue))

        # verify it no longer exists
        self.assertFalse(self.controller.exists(project, queue))

        # verify it isn't listable
        self.assertEqual(len(list(self.controller.list(project))), 0)

    def test_list(self):
        with helpers.entries(self.controller, 10) as expect:
            values = zip(self.controller.list(u'_'), expect)
            for e, x in values:
                p, q, n, h = x
                self._check_structure(e)
                self._check_value(e, xname=q, xmeta={},
                                  xpartition=n, xhost=h)

    def test_get(self):
        with helpers.entry(self.controller, self.project, self.queue,
                           u'a', u'a') as expect:
            p, q, n, h, m = expect
            e = self.controller.get(p, q)
            self._check_value(e, xname=q, xmeta=m,
                              xpartition=n, xhost=h)

    def test_exists(self):
        with helpers.entry(self.controller, self.project, self.queue,
                           u'a', u'a') as expect:
            p, q, _, _, _ = expect
            self.assertTrue(self.controller.exists(p, q))

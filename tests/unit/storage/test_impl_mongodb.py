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

import os
import time

import mock
from pymongo import cursor
import pymongo.errors
from testtools import matchers

from marconi.common import exceptions
from marconi.queues import storage
from marconi.queues.storage import mongodb
from marconi.queues.storage.mongodb import controllers
from marconi.queues.storage.mongodb import options as mongodb_options
from marconi.queues.storage.mongodb import utils
from marconi import tests as testing
from marconi.tests.storage import base


class MongodbUtilsTest(testing.TestBase):

    def test_dup_marker_from_error(self):
        error_message = ('E11000 duplicate key error index: '
                         'marconi.messages.$queue_marker  dup key: '
                         '{ : "queue", : "project", : 3 }')

        marker = utils.dup_marker_from_error(error_message)
        self.assertEquals(marker, 3)

        error_message = ('E11000 duplicate key error index: '
                         'marconi.messages.$x_y  dup key: '
                         '{ : "queue", : "project", : 3 }')

        self.assertRaises(exceptions.PatternNotFound,
                          utils.dup_marker_from_error, error_message)

        error_message = ('E11000 duplicate key error index: '
                         'marconi.messages.$queue_marker  dup key: '
                         '{ : ObjectId("51adff46b100eb85d8a93a2d") }')

        self.assertRaises(exceptions.PatternNotFound,
                          utils.dup_marker_from_error, error_message)

    def test_calculate_backoff(self):
        sec = utils.calculate_backoff(0, 10, 2, 0)
        self.assertEquals(sec, 0)

        sec = utils.calculate_backoff(9, 10, 2, 0)
        self.assertEquals(sec, 1.8)

        sec = utils.calculate_backoff(4, 10, 2, 0)
        self.assertEquals(sec, 0.8)

        sec = utils.calculate_backoff(4, 10, 2, 1)
        if sec != 0.8:
            self.assertThat(sec, matchers.GreaterThan(0.8))
            self.assertThat(sec, matchers.LessThan(1.8))

        self.assertRaises(ValueError, utils.calculate_backoff, 0, 10, -2, -1)
        self.assertRaises(ValueError, utils.calculate_backoff, 0, 10, -2, 0)
        self.assertRaises(ValueError, utils.calculate_backoff, 0, 10, 2, -1)

        self.assertRaises(ValueError, utils.calculate_backoff, -2, -10, 2, 0)
        self.assertRaises(ValueError, utils.calculate_backoff, 2, -10, 2, 0)
        self.assertRaises(ValueError, utils.calculate_backoff, -2, 10, 2, 0)
        self.assertRaises(ValueError, utils.calculate_backoff, -1, 10, 2, 0)
        self.assertRaises(ValueError, utils.calculate_backoff, 10, 10, 2, 0)
        self.assertRaises(ValueError, utils.calculate_backoff, 11, 10, 2, 0)


class MongodbDriverTest(testing.TestBase):

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance running')

        super(MongodbDriverTest, self).setUp()
        self.load_conf('wsgi_mongodb.conf')

    def test_db_instance(self):
        driver = mongodb.Driver()
        db = driver.db
        self.assertEquals(db.name, mongodb_options.CFG.database)


class MongodbQueueTests(base.QueueControllerTest):

    driver_class = mongodb.Driver
    controller_class = controllers.QueueController

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance running')

        super(MongodbQueueTests, self).setUp()
        self.load_conf('wsgi_mongodb.conf')

    def tearDown(self):
        self.controller._col.drop()
        super(MongodbQueueTests, self).tearDown()

    def test_indexes(self):
        col = self.controller._col
        indexes = col.index_information()
        self.assertIn('p_1_n_1', indexes)

    def test_messages_purged(self):
        queue_name = 'test'
        self.controller.create(queue_name)
        self.message_controller.post(queue_name,
                                     [{'ttl': 60}],
                                     1234)
        self.controller.delete(queue_name)
        col = self.message_controller._col
        self.assertEqual(col.find({'q': queue_name}).count(), 0)

    def test_raises_connection_error(self):

        with mock.patch.object(cursor.Cursor, 'next', autospec=True) as method:
            error = pymongo.errors.ConnectionFailure()
            method.side_effect = error

            queues = next(self.controller.list())
            self.assertRaises(storage.exceptions.ConnectionError, queues.next)


class MongodbMessageTests(base.MessageControllerTest):

    driver_class = mongodb.Driver
    controller_class = controllers.MessageController

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance running')

        super(MongodbMessageTests, self).setUp()
        self.load_conf('wsgi_mongodb.conf')

    def tearDown(self):
        self.controller._col.drop()
        super(MongodbMessageTests, self).tearDown()

    def _count_expired(self, queue, project=None):
        return self.controller._count_expired(queue, project)

    def test_indexes(self):
        col = self.controller._col
        indexes = col.index_information()
        self.assertIn('active', indexes)
        self.assertIn('claimed', indexes)
        self.assertIn('queue_marker', indexes)
        self.assertIn('counting', indexes)

    def test_next_marker(self):
        queue_name = 'marker_test'
        iterations = 10

        self.queue_controller.create(queue_name)

        seed_marker1 = self.controller._next_marker(queue_name)
        self.assertEqual(seed_marker1, 1, 'First marker is 1')

        for i in range(iterations):
            self.controller.post(queue_name, [{'ttl': 60}], 'uuid')
            marker1 = self.controller._next_marker(queue_name)
            marker2 = self.controller._next_marker(queue_name)
            marker3 = self.controller._next_marker(queue_name)
            self.assertEqual(marker1, marker2)
            self.assertEqual(marker2, marker3)

            self.assertEqual(marker1, i + 2)

    def test_remove_expired(self):
        num_projects = 10
        num_queues = 10
        messages_per_queue = 100

        projects = ['gc-test-project-{0}'.format(i)
                    for i in range(num_projects)]

        queue_names = ['gc-test-{0}'.format(i) for i in range(num_queues)]
        client_uuid = 'b623c53c-cf75-11e2-84e1-a1187188419e'
        messages = [{'ttl': 0, 'body': str(i)}
                    for i in range(messages_per_queue)]

        for project in projects:
            for queue in queue_names:
                self.queue_controller.create(queue, project)
                self.controller.post(queue, messages, client_uuid, project)

        self.controller.remove_expired()

        for project in projects:
            for queue in queue_names:
                query = {'q': queue, 'p': project}

                cursor = self.driver.db.messages.find(query)
                count = cursor.count()

                # Expect that the most recent message for each queue
                # will not be removed.
                self.assertEquals(count, 1)

                message = next(cursor)
                self.assertEquals(message['k'], messages_per_queue)

    def test_empty_queue_exception(self):
        queue_name = 'empty-queue-test'
        self.queue_controller.create(queue_name)

        self.assertRaises(storage.exceptions.QueueIsEmpty,
                          self.controller.first, queue_name)

    def test_invalid_sort_option(self):
        queue_name = 'empty-queue-test'
        self.queue_controller.create(queue_name)

        self.assertRaises(ValueError,
                          self.controller.first, queue_name, sort=0)


class MongodbClaimTests(base.ClaimControllerTest):
    driver_class = mongodb.Driver
    controller_class = controllers.ClaimController

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance running')

        super(MongodbClaimTests, self).setUp()
        self.load_conf('wsgi_mongodb.conf')

    def test_claim_doesnt_exist(self):
        """Verifies that operations fail on expired/missing claims.

        Methods should raise an exception when the claim doesn't
        exists and/or has expired.
        """
        epoch = '000000000000000000000000'
        self.assertRaises(storage.exceptions.ClaimDoesNotExist,
                          self.controller.get, self.queue_name,
                          epoch, project=self.project)

        claim_id, messages = self.controller.create(self.queue_name,
                                                    {'ttl': 1, 'grace': 0},
                                                    project=self.project)

        # Lets let it expire
        time.sleep(1)
        self.assertRaises(storage.exceptions.ClaimDoesNotExist,
                          self.controller.update, self.queue_name,
                          claim_id, {}, project=self.project)

        self.assertRaises(storage.exceptions.ClaimDoesNotExist,
                          self.controller.update, self.queue_name,
                          claim_id, {}, project=self.project)

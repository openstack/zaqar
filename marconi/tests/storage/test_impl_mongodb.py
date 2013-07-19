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
import random
import time

import mock
from pymongo import cursor
import pymongo.errors
from testtools import matchers

from marconi.common import exceptions
from marconi import storage
from marconi.storage import mongodb
from marconi.storage.mongodb import controllers
from marconi.storage.mongodb import options as mongodb_options
from marconi.storage.mongodb import utils
from marconi.tests.storage import base
from marconi.tests import util as testing


class MongodbUtilsTest(testing.TestBase):

    def test_dup_marker_from_error(self):
        error_message = ('E11000 duplicate key error index: '
                         'marconi.messages.$queue_marker  dup key: '
                         '{ : ObjectId("51adff46b100eb85d8a93a2d"), : 3 }')

        marker = utils.dup_marker_from_error(error_message)
        self.assertEquals(marker, 3)

        error_message = ('E11000 duplicate key error index: '
                         'marconi.messages.$x_y  dup key: '
                         '{ : ObjectId("51adff46b100eb85d8a93a2d"), : 3 }')

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
        self.controller.upsert(queue_name, {})
        qid = self.controller._get_id(queue_name)
        self.message_controller.post(queue_name,
                                     [{'ttl': 60}],
                                     1234)
        self.controller.delete(queue_name)
        col = self.message_controller._col
        self.assertEqual(col.find({'q': qid}).count(), 0)

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
        queue_id = self.queue_controller._get_id(queue, project)
        return self.controller._count_expired(queue_id)

    def test_indexes(self):
        col = self.controller._col
        indexes = col.index_information()
        self.assertIn('active', indexes)
        self.assertIn('claimed', indexes)
        self.assertIn('queue_marker', indexes)

    def test_next_marker(self):
        queue_name = 'marker_test'
        iterations = 10

        self.queue_controller.upsert(queue_name, {})
        queue_id = self.queue_controller._get_id(queue_name)

        seed_marker1 = self.controller._next_marker(queue_name)
        self.assertEqual(seed_marker1, 1, 'First marker is 1')

        for i in range(iterations):
            self.controller.post(queue_name, [{'ttl': 60}], 'uuid')
            marker1 = self.controller._next_marker(queue_id)
            marker2 = self.controller._next_marker(queue_id)
            marker3 = self.controller._next_marker(queue_id)
            self.assertEqual(marker1, marker2)
            self.assertEqual(marker2, marker3)

            self.assertEqual(marker1, i + 2)

    def test_remove_expired(self):
        num_projects = 10
        num_queues = 10
        total_queues = num_projects * num_queues
        gc_threshold = mongodb_options.CFG.gc_threshold
        messages_per_queue = gc_threshold
        nogc_messages_per_queue = gc_threshold - 1

        projects = ['gc-test-project-%s' % i for i in range(num_projects)]
        queue_names = ['gc-test-%s' % i for i in range(num_queues)]
        client_uuid = 'b623c53c-cf75-11e2-84e1-a1187188419e'
        messages = [{'ttl': 0, 'body': str(i)}
                    for i in range(messages_per_queue)]

        for project in projects:
            for queue in queue_names:
                self.queue_controller.upsert(queue, {}, project)
                self.controller.post(queue, messages, client_uuid, project)

        # Add one that should not be gc'd due to being under threshold
        self.queue_controller.upsert('nogc-test', {}, 'nogc-test-project')
        nogc_messages = [{'ttl': 0, 'body': str(i)}
                         for i in range(nogc_messages_per_queue)]
        self.controller.post('nogc-test', nogc_messages,
                             client_uuid, 'nogc-test-project')

        total_expired = sum(
            self._count_expired(queue, project)
            for queue in queue_names
            for project in projects)

        self.assertEquals(total_expired, total_queues * messages_per_queue)
        self.controller.remove_expired()

        # Make sure the messages in this queue were not gc'd since
        # the count was under the threshold.
        self.assertEquals(
            self._count_expired('nogc-test', 'nogc-test-project'),
            len(nogc_messages))

        total_expired = sum(
            self._count_expired(queue, project)
            for queue in queue_names
            for project in projects)

        # Expect that the most recent message for each queue
        # will not be removed.
        self.assertEquals(total_expired, total_queues)

        # Sanity-check that the most recent message is the
        # one remaining in the queue.
        queue = random.choice(queue_names)
        queue_id = self.queue_controller._get_id(queue, project)
        message = self.driver.db.messages.find_one({'q': queue_id})
        self.assertEquals(message['k'], messages_per_queue)


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

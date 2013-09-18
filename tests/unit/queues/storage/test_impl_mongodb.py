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

from marconi.openstack.common import timeutils
from marconi.queues import storage
from marconi.queues.storage import exceptions
from marconi.queues.storage import mongodb
from marconi.queues.storage.mongodb import controllers
from marconi.queues.storage.mongodb import options as mongodb_options
from marconi.queues.storage.mongodb import utils
from marconi import tests as testing
from marconi.tests.queues.storage import base


class MongodbUtilsTest(testing.TestBase):

    def test_scope_queue_name(self):
        self.assertEquals(utils.scope_queue_name('my-q'), '/my-q')
        self.assertEquals(utils.scope_queue_name('my-q', None), '/my-q')
        self.assertEquals(utils.scope_queue_name('my-q', '123'), '123/my-q')

        self.assertEquals(utils.scope_queue_name(None), '/')
        self.assertEquals(utils.scope_queue_name(None, '123'), '123/')

    def test_descope_queue_name(self):
        self.assertEquals(utils.descope_queue_name('/'), None)
        self.assertEquals(utils.descope_queue_name('/some-pig'), 'some-pig')
        self.assertEquals(utils.descope_queue_name('radiant/some-pig'),
                          'some-pig')

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
        self.message_controller._col.drop()
        super(MongodbQueueTests, self).tearDown()

    def test_indexes(self):
        col = self.controller._col
        indexes = col.index_information()
        self.assertIn('p_q_1', indexes)

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

    # NOTE(kgriffs): MongoDB's TTL scavenger only runs once a minute
    gc_interval = 60

    def setUp(self):
        if not os.environ.get('MONGODB_TEST_LIVE'):
            self.skipTest('No MongoDB instance running')

        super(MongodbMessageTests, self).setUp()
        self.load_conf('wsgi_mongodb.conf')

    def tearDown(self):
        self.controller._col.drop()
        self.queue_controller._col.drop()
        super(MongodbMessageTests, self).tearDown()

    def test_indexes(self):
        col = self.controller._col
        indexes = col.index_information()
        self.assertIn('active', indexes)
        self.assertIn('claimed', indexes)
        self.assertIn('queue_marker', indexes)
        self.assertIn('counting', indexes)

    def test_message_counter(self):
        queue_name = 'marker_test'
        iterations = 10

        self.queue_controller.create(queue_name)

        seed_marker1 = self.queue_controller._get_counter(queue_name)
        self.assertEqual(seed_marker1, 1, 'First marker is 1')

        for i in range(iterations):
            self.controller.post(queue_name, [{'ttl': 60}], 'uuid')

            marker1 = self.queue_controller._get_counter(queue_name)
            marker2 = self.queue_controller._get_counter(queue_name)
            marker3 = self.queue_controller._get_counter(queue_name)

            self.assertEqual(marker1, marker2)
            self.assertEqual(marker2, marker3)
            self.assertEqual(marker1, i + 2)

        new_value = self.queue_controller._inc_counter(queue_name)
        self.assertIsNotNone(new_value)

        value_before = self.queue_controller._get_counter(queue_name)
        new_value = self.queue_controller._inc_counter(queue_name)
        self.assertIsNotNone(new_value)
        value_after = self.queue_controller._get_counter(queue_name)
        self.assertEquals(value_after, value_before + 1)

        value_before = value_after
        new_value = self.queue_controller._inc_counter(queue_name, amount=7)
        value_after = self.queue_controller._get_counter(queue_name)
        self.assertEquals(value_after, value_before + 7)
        self.assertEquals(value_after, new_value)

        reference_value = value_after

        unchanged = self.queue_controller._inc_counter(queue_name, window=10)
        self.assertIsNone(unchanged)

        # TODO(kgriffs): Pass utcnow to work around bug
        # in set_time_override until we merge the fix in
        # from upstream.
        timeutils.set_time_override(timeutils.utcnow())

        timeutils.advance_time_seconds(10)
        changed = self.queue_controller._inc_counter(queue_name, window=5)
        self.assertEquals(changed, reference_value + 1)
        timeutils.clear_time_override()

    def test_race_condition_on_post(self):
        queue_name = 'marker_test'
        self.queue_controller.create(queue_name)

        expected_messages = [
            {
                'ttl': 60,
                'body': {
                    'event': 'BackupStarted',
                    'backupId': 'c378813c-3f0b-11e2-ad92-7823d2b0f3ce',
                },
            },
            {
                'ttl': 60,
                'body': {
                    'event': 'BackupStarted',
                    'backupId': 'd378813c-3f0b-11e2-ad92-7823d2b0f3ce',
                },
            },
            {
                'ttl': 60,
                'body': {
                    'event': 'BackupStarted',
                    'backupId': 'e378813c-3f0b-11e2-ad92-7823d2b0f3ce',
                },
            },
        ]

        uuid = '97b64000-2526-11e3-b088-d85c1300734c'

        # NOTE(kgriffs): Patch _inc_counter so it is a noop, so that
        # the second time we post, we will get a collision. This simulates
        # what happens when we have parallel requests and the "winning"
        # requests hasn't gotten around to calling _inc_counter before the
        # "losing" request attempts to insert it's batch of messages.
        with mock.patch.object(mongodb.queues.QueueController,
                               '_inc_counter', autospec=True) as method:

            method.return_value = 2
            messages = expected_messages[:1]
            created = list(self.controller.post(queue_name, messages, uuid))
            self.assertEquals(len(created), 1)

            # Force infinite retries
            if testing.RUN_SLOW_TESTS:
                method.return_value = None

                with testing.expect(exceptions.MessageConflict):
                    self.controller.post(queue_name, messages, uuid)

        created = list(self.controller.post(queue_name,
                                            expected_messages[1:],
                                            uuid))

        self.assertEquals(len(created), 2)

        expected_ids = [m['body']['backupId'] for m in expected_messages]

        interaction = self.controller.list(queue_name, client_uuid=uuid,
                                           echo=True)
        actual_messages = list(next(interaction))
        self.assertEquals(len(actual_messages), len(expected_messages))
        actual_ids = [m['body']['backupId'] for m in actual_messages]

        self.assertEquals(actual_ids, expected_ids)

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

    def tearDown(self):
        self.message_controller._col.drop()
        self.queue_controller._col.drop()
        super(MongodbClaimTests, self).tearDown()

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

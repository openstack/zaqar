# Copyright (c) 2013 Red Hat, Inc.
# Copyright (c) 2014 Catalyst IT Ltd.
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

import collections
import datetime
import math
import random
import time
import uuid

import ddt
import mock
from oslo_utils import timeutils
import six
from testtools import matchers

from zaqar.common import cache as oslo_cache
from zaqar import storage
from zaqar.storage import errors
from zaqar.storage import pipeline
from zaqar import tests as testing
from zaqar.tests import helpers


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
                              self.controller_class,
                              self.controller_base_class))

        oslo_cache.register_config(self.conf)
        cache = oslo_cache.get_cache(self.conf)

        pooling = 'pooling' in self.conf and self.conf.pooling
        if pooling and not self.control_driver_class:
            self.skipTest("Pooling is enabled, "
                          "but control driver class is not specified")

        self.control = self.control_driver_class(self.conf, cache)
        if not pooling:
            args = [self.conf, cache]
            if issubclass(self.driver_class, storage.DataDriverBase):
                args.append(self.control)
            self.driver = self.driver_class(*args)
        else:
            uri = self.mongodb_url
            for i in range(4):
                db_name = "zaqar_test_pools_" + str(i)

                # NOTE(dynarro): we need to create a unique uri.
                uri = "%s/%s" % (uri, db_name)
                options = {'database': db_name}
                self.control.pools_controller.create(six.text_type(i),
                                                     100, uri, options=options)
            self.driver = self.driver_class(self.conf, cache, self.control)
            self.addCleanup(self.control.pools_controller.drop_all)
            self.addCleanup(self.control.catalogue_controller.drop_all)

        self._prepare_conf()

        self.addCleanup(self._purge_databases)

        if not pooling:
            self.controller = self.controller_class(self.driver)
        else:
            self.controller = self.controller_class(self.driver._pool_catalog)

        self.pipeline = pipeline.DataDriver(self.conf,
                                            self.driver,
                                            self.control)

    def _prepare_conf(self):
        """Prepare the conf before running tests

        Classes overriding this method, must use
        the `self.conf` instance and alter its state.
        """

    def _purge_databases(self):
        """Override to clean databases."""


@ddt.ddt
class QueueControllerTest(ControllerBaseTest):
    """Queue Controller base tests."""
    controller_base_class = storage.Queue

    def setUp(self):
        super(QueueControllerTest, self).setUp()
        self.queue_controller = self.pipeline.queue_controller

    @ddt.data(None, ControllerBaseTest.project)
    def test_list(self, project):
        # NOTE(kgriffs): Ensure we mix global and scoped queues
        # in order to verify that queue records are excluded that
        # are not at the same level.
        project_alt = self.project if project is None else None

        num = 15
        for queue in six.moves.xrange(num):
            queue = str(queue)
            self.controller.create(queue, project=project)
            self.controller.create(queue, project=project_alt)
            self.addCleanup(self.controller.delete,
                            queue, project=project)
            self.addCleanup(self.controller.delete,
                            queue, project=project_alt)

        interaction = self.controller.list(project=project,
                                           detailed=True)
        queues = list(next(interaction))

        self.assertTrue(all(map(lambda queue:
                                'name' in queue and
                                'metadata' in queue, queues)))
        self.assertEqual(10, len(queues))

        interaction = self.controller.list(project=project,
                                           marker=next(interaction))
        queues = list(next(interaction))

        self.assertTrue(all(map(lambda queue:
                                'name' in queue and
                                'metadata' not in queue, queues)))

        self.assertEqual(5, len(queues))

    def test_queue_lifecycle(self):
        # Test queue creation
        created = self.controller.create('test',
                                         metadata=dict(meta='test_meta'),
                                         project=self.project)
        self.assertTrue(created)

        # Test queue existence
        self.assertTrue(self.controller.exists('test', project=self.project))

        # Test queue retrieval
        interaction = self.controller.list(project=self.project)
        queue = list(next(interaction))[0]
        self.assertEqual('test', queue['name'])

        # Test queue metadata retrieval
        metadata = self.controller.get('test', project=self.project)
        self.assertEqual('test_meta', metadata['meta'])

        # Touching an existing queue does not affect metadata
        created = self.controller.create('test', project=self.project)
        self.assertFalse(created)

        metadata = self.controller.get('test', project=self.project)
        self.assertEqual('test_meta', metadata['meta'])

        # Test queue deletion
        self.controller.delete('test', project=self.project)

        # Test queue existence
        self.assertFalse(self.controller.exists('test', project=self.project))


class MessageControllerTest(ControllerBaseTest):
    """Message Controller base tests.

    NOTE(flaper87): Implementations of this class should
    override the tearDown method in order
    to clean up storage's state.
    """
    queue_name = 'test_queue'
    controller_base_class = storage.Message

    # Specifies how often expired messages are purged, in sec.
    gc_interval = 0

    def setUp(self):
        super(MessageControllerTest, self).setUp()

        # Lets create a queue
        self.queue_controller = self.pipeline.queue_controller
        self.claim_controller = self.pipeline.claim_controller
        self.queue_controller.create(self.queue_name, project=self.project)

    def tearDown(self):
        self.queue_controller.delete(self.queue_name, project=self.project)
        super(MessageControllerTest, self).tearDown()

    def test_stats_for_empty_queue(self):
        self.addCleanup(self.queue_controller.delete, 'test',
                        project=self.project)
        created = self.queue_controller.create('test', project=self.project)
        self.assertTrue(created)

        stats = self.queue_controller.stats('test', project=self.project)
        message_stats = stats['messages']

        self.assertEqual(0, message_stats['free'])
        self.assertEqual(0, message_stats['claimed'])
        self.assertEqual(0, message_stats['total'])

        self.assertNotIn('newest', message_stats)
        self.assertNotIn('oldest', message_stats)

    def test_queue_count_on_bulk_delete(self):
        self.addCleanup(self.queue_controller.delete, 'test-queue',
                        project=self.project)
        queue_name = 'test-queue'
        client_uuid = uuid.uuid4()

        created = self.queue_controller.create(queue_name,
                                               project=self.project)
        self.assertTrue(created)

        # Create 10 messages.
        msg_keys = _insert_fixtures(self.controller, queue_name,
                                    project=self.project,
                                    client_uuid=client_uuid, num=10)

        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']
        self.assertEqual(10, stats['total'])

        # Delete 5 messages
        self.controller.bulk_delete(queue_name, msg_keys[0:5],
                                    self.project)
        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']
        self.assertEqual(5, stats['total'])

    def test_queue_count_on_bulk_delete_with_invalid_id(self):
        self.addCleanup(self.queue_controller.delete, 'test-queue',
                        project=self.project)
        queue_name = 'test-queue'
        client_uuid = uuid.uuid4()

        created = self.queue_controller.create(queue_name,
                                               project=self.project)
        self.assertTrue(created)

        # Create 10 messages.
        msg_keys = _insert_fixtures(self.controller, queue_name,
                                    project=self.project,
                                    client_uuid=client_uuid, num=10)

        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']
        self.assertEqual(10, stats['total'])

        # Delete 5 messages
        self.controller.bulk_delete(queue_name,
                                    msg_keys[0:5] + ['invalid'],
                                    self.project)

        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']
        self.assertEqual(5, stats['total'])

    def test_queue_count_on_delete(self):
        self.addCleanup(self.queue_controller.delete, 'test-queue',
                        project=self.project)
        queue_name = 'test-queue'
        client_uuid = uuid.uuid4()

        created = self.queue_controller.create(queue_name,
                                               project=self.project)
        self.assertTrue(created)

        # Create 10 messages.
        msg_keys = _insert_fixtures(self.controller, queue_name,
                                    project=self.project,
                                    client_uuid=client_uuid, num=10)

        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']
        self.assertEqual(10, stats['total'])

        # Delete 1 message
        self.controller.delete(queue_name, msg_keys[0], self.project)
        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']
        self.assertEqual(9, stats['total'])

    def test_queue_stats(self):
        # Test queue creation
        self.addCleanup(self.queue_controller.delete, 'test',
                        project=self.project)
        created = self.queue_controller.create('test',
                                               metadata=dict(meta='test_meta'),
                                               project=self.project)

        client_uuid = uuid.uuid4()
        # Test queue statistic
        _insert_fixtures(self.controller, 'test',
                         project=self.project, client_uuid=client_uuid,
                         num=6)

        # NOTE(kgriffs): We can't get around doing this, because
        # we don't know how the storage drive may be calculating
        # message timestamps (and may not be monkey-patchable).
        time.sleep(1.2)

        _insert_fixtures(self.controller, 'test',
                         project=self.project, client_uuid=client_uuid,
                         num=6)

        stats = self.queue_controller.stats('test', project=self.project)
        message_stats = stats['messages']

        self.assertEqual(12, message_stats['free'])
        self.assertEqual(0, message_stats['claimed'])
        self.assertEqual(12, message_stats['total'])

        oldest = message_stats['oldest']
        newest = message_stats['newest']

        self.assertNotEqual(oldest, newest)

        age = oldest['age']
        self.assertThat(age, matchers.GreaterThan(0))

        # NOTE(kgriffs): Ensure is different enough
        # for the next comparison to work.
        soon = timeutils.utcnow() + datetime.timedelta(seconds=60)

        for message_stat in (oldest, newest):
            created_iso = message_stat['created']
            created = timeutils.parse_isotime(created_iso)
            self.assertThat(timeutils.normalize_time(created),
                            matchers.LessThan(soon))

            self.assertIn('id', message_stat)

        self.assertThat(oldest['created'],
                        matchers.LessThan(newest['created']))

    def test_queue_count_on_claim_delete(self):
        self.addCleanup(self.queue_controller.delete, 'test-queue',
                        project=self.project)
        queue_name = 'test-queue'
        client_uuid = uuid.uuid4()

        created = self.queue_controller.create(queue_name,
                                               project=self.project)
        self.assertTrue(created)

        # Create 15 messages.
        msg_keys = _insert_fixtures(self.controller, queue_name,
                                    project=self.project,
                                    client_uuid=client_uuid, num=15)

        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']
        self.assertEqual(15, stats['total'])

        metadata = {'ttl': 120, 'grace': 60}
        # Claim 10 messages
        claim_id, _ = self.claim_controller.create(queue_name, metadata,
                                                   self.project)

        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']
        self.assertEqual(10, stats['claimed'])

        # Delete one message and ensure stats are updated even
        # thought the claim itself has not been deleted.
        self.controller.delete(queue_name, msg_keys[0],
                               self.project, claim_id)
        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']
        self.assertEqual(14, stats['total'])
        self.assertEqual(9, stats['claimed'])
        self.assertEqual(5, stats['free'])

        # Same thing but use bulk_delete interface
        self.controller.bulk_delete(queue_name, msg_keys[1:3],
                                    self.project)
        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']
        self.assertEqual(12, stats['total'])
        self.assertEqual(7, stats['claimed'])
        self.assertEqual(5, stats['free'])

        # Delete the claim
        self.claim_controller.delete(queue_name, claim_id,
                                     self.project)
        stats = self.queue_controller.stats(queue_name,
                                            self.project)['messages']

        self.assertEqual(0, stats['claimed'])

    def test_message_lifecycle(self):
        queue_name = self.queue_name

        message = {
            'ttl': 60,
            'body': {
                'event': 'BackupStarted',
                'backupId': 'c378813c-3f0b-11e2-ad92-7823d2b0f3ce'
            }
        }

        # Test Message Creation
        created = list(self.controller.post(queue_name, [message],
                                            project=self.project,
                                            client_uuid=uuid.uuid4()))
        self.assertEqual(1, len(created))
        message_id = created[0]

        # Test Message Get
        message_out = self.controller.get(queue_name, message_id,
                                          project=self.project)
        self.assertEqual({'id', 'body', 'ttl', 'age', 'claim_id'},
                         set(message_out))
        self.assertEqual(message_id, message_out['id'])
        self.assertEqual(message['body'], message_out['body'])
        self.assertEqual(message['ttl'], message_out['ttl'])

        # Test Message Deletion
        self.controller.delete(queue_name, message_id, project=self.project)

        # Test does not exist
        with testing.expect(errors.DoesNotExist):
            self.controller.get(queue_name, message_id, project=self.project)

    def test_get_multi(self):
        client_uuid = uuid.uuid4()

        _insert_fixtures(self.controller, self.queue_name,
                         project=self.project, client_uuid=client_uuid, num=15)

        def load_messages(expected, *args, **kwargs):
            interaction = self.controller.list(*args, **kwargs)
            msgs = list(next(interaction))
            self.assertEqual(expected, len(msgs))
            return interaction

        # Test all messages, echo False and uuid
        load_messages(0, self.queue_name, project=self.project,
                      client_uuid=client_uuid)

        # Test all messages and limit
        load_messages(15, self.queue_name, project=self.project, limit=20,
                      echo=True)

        # Test default limit
        load_messages(storage.DEFAULT_MESSAGES_PER_PAGE,
                      self.queue_name, project=self.project, echo=True)

        # Test all messages, echo True, and uuid
        interaction = load_messages(10, self.queue_name, echo=True,
                                    project=self.project,
                                    client_uuid=client_uuid)

        # Test all messages, echo True, uuid and marker
        load_messages(5, self.queue_name, echo=True, project=self.project,
                      marker=next(interaction), client_uuid=client_uuid)

    def test_multi_ids(self):
        messages_in = [{'ttl': 120, 'body': 0}, {'ttl': 240, 'body': 1}]
        ids = self.controller.post(self.queue_name, messages_in,
                                   project=self.project,
                                   client_uuid=uuid.uuid4())

        messages_out = self.controller.bulk_get(self.queue_name, ids,
                                                project=self.project)

        for idx, message in enumerate(messages_out):
            self.assertEqual({'id', 'body', 'ttl', 'age', 'claim_id'},
                             set(message))
            self.assertEqual(idx, message['body'])

        self.controller.bulk_delete(self.queue_name, ids,
                                    project=self.project)

        with testing.expect(StopIteration):
            result = self.controller.bulk_get(self.queue_name, ids,
                                              project=self.project)
            next(result)

    def test_claim_effects(self):
        client_uuid = uuid.uuid4()

        _insert_fixtures(self.controller, self.queue_name,
                         project=self.project, client_uuid=client_uuid, num=12)

        def list_messages(include_claimed=None):
            kwargs = {
                'project': self.project,
                'client_uuid': client_uuid,
                'echo': True,
            }

            # Properly test default value
            if include_claimed is not None:
                kwargs['include_claimed'] = include_claimed

            interaction = self.controller.list(self.queue_name, **kwargs)

            messages = next(interaction)
            return [msg['id'] for msg in messages]

        messages_before = list_messages(True)

        meta = {'ttl': 70, 'grace': 60}
        another_cid, _ = self.claim_controller.create(self.queue_name, meta,
                                                      project=self.project)

        messages_after = list_messages(True)
        self.assertEqual(messages_before, messages_after)

        messages_excluding_claimed = list_messages()
        self.assertNotEqual(messages_before, messages_excluding_claimed)
        self.assertEqual(2, len(messages_excluding_claimed))

        cid, msgs = self.claim_controller.create(self.queue_name, meta,
                                                 project=self.project)
        [msg1, msg2] = msgs

        # A wrong claim does not ensure the message deletion
        with testing.expect(errors.NotPermitted):
            self.controller.delete(self.queue_name, msg1['id'],
                                   project=self.project,
                                   claim=another_cid)

        # Make sure a message can be deleted with a claim
        self.controller.delete(self.queue_name, msg1['id'],
                               project=self.project,
                               claim=cid)

        with testing.expect(errors.DoesNotExist):
            self.controller.get(self.queue_name, msg1['id'],
                                project=self.project)

        # Make sure such a deletion is idempotent
        self.controller.delete(self.queue_name, msg1['id'],
                               project=self.project,
                               claim=cid)

        # A non-existing claim does not ensure the message deletion
        self.claim_controller.delete(self.queue_name, cid,
                                     project=self.project)

        # NOTE(kgriffs) Message is no longer claimed, but try
        # to delete it with the claim anyway. It should raise
        # an error, because the client needs a hint that
        # perhaps the claim expired before it got around to
        # trying to delete the message, which means another
        # worker could be processing this message now.
        with testing.expect(errors.NotPermitted, errors.ClaimDoesNotExist):
            self.controller.delete(self.queue_name, msg2['id'],
                                   project=self.project,
                                   claim=cid)

    @testing.is_slow(condition=lambda self: self.gc_interval > 1)
    def test_expired_messages(self):
        messages = [{'body': 3.14, 'ttl': 1}, {'body': 0.618, 'ttl': 600}]
        client_uuid = uuid.uuid4()

        [msgid_expired, msgid] = self.controller.post(self.queue_name,
                                                      messages,
                                                      project=self.project,
                                                      client_uuid=client_uuid)

        # NOTE(kgriffs): Allow for automatic GC of claims, messages
        for i in range(self.gc_interval):
            time.sleep(1)

            # NOTE(kgriffs): Some drivers require a manual GC to be
            # triggered to clean up claims and messages.
            self.driver.gc()

            try:
                self.controller.get(self.queue_name, msgid_expired,
                                    project=self.project)
            except errors.DoesNotExist:
                break
        else:
            self.fail("Didn't remove the queue")

        # Make sure expired messages not return when listing
        interaction = self.controller.list(self.queue_name,
                                           project=self.project)

        messages = list(next(interaction))
        self.assertEqual(1, len(messages))
        self.assertEqual(msgid, messages[0]['id'])

        stats = self.queue_controller.stats(self.queue_name,
                                            project=self.project)
        self.assertEqual(1, stats['messages']['free'])

        # Make sure expired messages not return when popping
        messages = self.controller.pop(self.queue_name,
                                       limit=10,
                                       project=self.project)
        self.assertEqual(1, len(messages))
        self.assertEqual(msgid, messages[0]['id'])

    def test_bad_id(self):
        # NOTE(cpp-cabrera): A malformed ID should result in an empty
        # query. Raising an exception for validating IDs makes the
        # implementation more verbose instead of taking advantage of
        # the Maybe/Optional protocol, particularly when dealing with
        # bulk operations.
        bad_message_id = 'xyz'
        self.controller.delete(self.queue_name,
                               bad_message_id,
                               project=self.project)

        with testing.expect(errors.MessageDoesNotExist):
            self.controller.get(self.queue_name,
                                bad_message_id,
                                project=self.project)

    def test_bad_claim_id(self):
        [msgid] = self.controller.post(self.queue_name,
                                       [{'body': {}, 'ttl': 10}],
                                       project=self.project,
                                       client_uuid=uuid.uuid4())

        # NOTE(kgriffs): If the client has a typo or
        # something, they will need a hint that the
        # request was invalid.
        #
        # On the other hand, if they are actually
        # probing for a vulnerability, telling them
        # the claim they requested doesn't exist should
        # be harmless.
        with testing.expect(storage.errors.ClaimDoesNotExist):
            bad_claim_id = '; DROP TABLE queues'
            self.controller.delete(self.queue_name,
                                   msgid,
                                   project=self.project,
                                   claim=bad_claim_id)

    def test_bad_marker(self):
        bad_marker = 'xyz'
        interaction = self.controller.list(self.queue_name,
                                           project=self.project,
                                           client_uuid=uuid.uuid4(),
                                           marker=bad_marker)
        messages = list(next(interaction))

        self.assertEqual([], messages)

    def test_sort_for_first(self):
        client_uuid = uuid.uuid4()

        [msgid_first] = self.controller.post(self.queue_name,
                                             [{'body': {}, 'ttl': 120}],
                                             project=self.project,
                                             client_uuid=client_uuid)

        _insert_fixtures(self.controller, self.queue_name,
                         project=self.project, client_uuid=client_uuid, num=10)

        [msgid_last] = self.controller.post(self.queue_name,
                                            [{'body': {}, 'ttl': 120}],
                                            project=self.project,
                                            client_uuid=client_uuid)

        msg_asc = self.controller.first(self.queue_name,
                                        self.project,
                                        1)
        self.assertEqual(msgid_first, msg_asc['id'])

        msg_desc = self.controller.first(self.queue_name,
                                         self.project,
                                         -1)
        self.assertEqual(msgid_last, msg_desc['id'])

    def test_get_first_with_empty_queue_exception(self):
        self.assertRaises(errors.QueueIsEmpty,
                          self.controller.first,
                          self.queue_name, project=self.project)

    def test_get_first_with_invalid_sort_option(self):
        self.assertRaises(ValueError,
                          self.controller.first,
                          self.queue_name, sort=0,
                          project=self.project)

    def test_pop_message(self):
        self.queue_controller.create(self.queue_name, project=self.project)
        messages = [
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

        client_uuid = uuid.uuid1()
        self.controller.post(self.queue_name, messages, client_uuid,
                             project=self.project)

        # Test Message Pop
        popped_messages = self.controller.pop(self.queue_name,
                                              limit=1,
                                              project=self.project)

        self.assertEqual(1, len(popped_messages))

    def test_message_period(self):
        self.queue_controller.create(self.queue_name, project=self.project)
        messages = [
            {
                'ttl': 60,
                'body': {
                    'event.data': 'BackupStarted',
                    'backupId': 'c378813c-3f0b-11e2-ad92-7823d2b0f3ce',
                },
            },
        ]

        client_uuid = uuid.uuid1()
        self.controller.post(self.queue_name, messages, client_uuid,
                             project=self.project)

        stored_messages = self.controller.list(self.queue_name,
                                               project=self.project)

        self.assertItemsEqual(['event.data', 'backupId'],
                              list(next(stored_messages))[0]['body'].keys())

    def test_delete_message_from_nonexistent_queue(self):
        queue_name = 'fake_name'
        message_id = 'fake_id'
        res = self.controller.delete(queue_name, message_id,
                                     project=self.project)
        self.assertIsNone(res)

    def test_delete_messages_with_ids_from__nonexistent_queue(self):
        queue_name = 'fake_name'
        message_ids = ['fake_id1', 'fake_id2']
        res = self.controller.bulk_delete(queue_name, message_ids,
                                          project=self.project)
        self.assertIsNone(res)

    def test_get_messages_with_ids_from__nonexistent_queue(self):
        queue_name = 'fake_name'
        message_ids = ['fake_id1', 'fake_id2']
        res = self.controller.bulk_get(queue_name, message_ids,
                                       project=self.project)

        self.assertIsInstance(res, collections.Iterable)
        self.assertEqual([], list(res))


class ClaimControllerTest(ControllerBaseTest):
    """Claim Controller base tests.

    NOTE(flaper87): Implementations of this class should
    override the tearDown method in order
    to clean up storage's state.
    """
    queue_name = 'test_queue'
    controller_base_class = storage.Claim

    def setUp(self):
        super(ClaimControllerTest, self).setUp()

        # Lets create a queue
        self.queue_controller = self.pipeline.queue_controller
        self.message_controller = self.pipeline.message_controller
        self.queue_controller.create(self.queue_name, project=self.project)

    def tearDown(self):
        self.queue_controller.delete(self.queue_name, project=self.project)
        super(ClaimControllerTest, self).tearDown()

    def test_claim_lifecycle(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid=uuid.uuid4(),
                         num=20)

        meta = {'ttl': 70, 'grace': 30}

        # Make sure create works
        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project,
                                                    limit=15)

        messages = list(messages)
        self.assertEqual(15, len(messages))

        # Ensure Queue stats
        countof = self.queue_controller.stats(self.queue_name,
                                              project=self.project)
        self.assertEqual(15, countof['messages']['claimed'])
        self.assertEqual(5, countof['messages']['free'])
        self.assertEqual(20, countof['messages']['total'])

        # Make sure get works
        claim, messages2 = self.controller.get(self.queue_name, claim_id,
                                               project=self.project)

        messages2 = list(messages2)
        self.assertEqual(15, len(messages2))
        for msg1, msg2 in zip(messages, messages2):
            self.assertEqual(msg1['body'], msg2['body'])
            self.assertEqual(msg1['claim_id'], msg2['claim_id'])
            self.assertEqual(msg1['id'], msg2['id'])
            self.assertEqual(msg1['ttl'], msg2['ttl'])
        self.assertEqual(70, claim['ttl'])
        self.assertEqual(claim_id, claim['id'])

        new_meta = {'ttl': 100, 'grace': 60}
        self.controller.update(self.queue_name, claim_id,
                               new_meta, project=self.project)

        # Make sure update works
        claim, messages2 = self.controller.get(self.queue_name, claim_id,
                                               project=self.project)

        messages2 = list(messages2)
        self.assertEqual(15, len(messages2))

        # TODO(zyuan): Add some tests to ensure the ttl is
        # extended/not-extended.
        for msg1, msg2 in zip(messages, messages2):
            self.assertEqual(msg1['body'], msg2['body'])

        self.assertEqual(new_meta['ttl'], claim['ttl'])
        self.assertEqual(claim_id, claim['id'])

        # Make sure delete works
        self.controller.delete(self.queue_name, claim_id,
                               project=self.project)

        self.assertRaises(errors.ClaimDoesNotExist,
                          self.controller.get, self.queue_name,
                          claim_id, project=self.project)

    def test_claim_create_default_limit_multi(self):
        num_claims = 5
        num_messages = storage.DEFAULT_MESSAGES_PER_CLAIM * num_claims

        # NOTE(kgriffs): + 1 on num_messages to check for off-by-one error
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid=uuid.uuid4(),
                         num=num_messages + 1)

        meta = {'ttl': 70, 'grace': 30}
        total_claimed = 0

        for _ in range(num_claims):
            claim_id, messages = self.controller.create(
                self.queue_name, meta, project=self.project)

            messages = list(messages)
            num_claimed = len(messages)
            self.assertEqual(storage.DEFAULT_MESSAGES_PER_CLAIM,
                             num_claimed)

            total_claimed += num_claimed

        self.assertEqual(num_messages, total_claimed)

    def test_extend_lifetime(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid=uuid.uuid4(),
                         num=20, ttl=120)

        meta = {'ttl': 777, 'grace': 0}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEqual(777, message['ttl'])

    def test_extend_lifetime_with_grace_1(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid=uuid.uuid4(),
                         num=20, ttl=120)

        meta = {'ttl': 777, 'grace': 23}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEqual(800, message['ttl'])

    def test_extend_lifetime_with_grace_2(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid=uuid.uuid4(),
                         num=20, ttl=120)

        meta = {'ttl': 121, 'grace': 22}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEqual(143, message['ttl'])

    def test_do_not_extend_lifetime(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid=uuid.uuid4(),
                         num=20, ttl=120)

        # Choose a ttl that is less than the message's current TTL
        meta = {'ttl': 60, 'grace': 30}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEqual(120, message['ttl'])

    def test_expired_claim(self):
        meta = {'ttl': 1, 'grace': 60}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)
        time.sleep(1)

        with testing.expect(errors.DoesNotExist):
            self.controller.get(self.queue_name, claim_id,
                                project=self.project)

        with testing.expect(errors.DoesNotExist):
            self.controller.update(self.queue_name, claim_id,
                                   meta, project=self.project)

    def test_delete_message_expired_claim(self):
        meta = {'ttl': 2, 'grace': 2}
        new_messages = [{'ttl': 60, 'body': {}},
                        {'ttl': 60, 'body': {}},
                        {'ttl': 60, 'body': {}}]

        self.message_controller.post(self.queue_name, new_messages,
                                     client_uuid=str(uuid.uuid1()),
                                     project=self.project)

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        now = timeutils.utcnow_ts()
        timeutils_utcnow = 'oslo_utils.timeutils.utcnow_ts'

        with mock.patch(timeutils_utcnow) as mock_utcnow:
            mock_utcnow.return_value = now + 2

            messages = [msg['id'] for msg in messages]
            self.message_controller.delete(self.queue_name,
                                           messages.pop(),
                                           project=self.project)

            self.message_controller.bulk_delete(self.queue_name,
                                                messages,
                                                project=self.project)

    def test_illformed_id(self):
        # any ill-formed IDs should be regarded as non-existing ones.

        self.controller.delete(self.queue_name,
                               'illformed',
                               project=self.project)

        with testing.expect(errors.DoesNotExist):
            self.controller.get(self.queue_name,
                                'illformed',
                                project=self.project)

        with testing.expect(errors.DoesNotExist):
            self.controller.update(self.queue_name,
                                   'illformed',
                                   {'ttl': 40},
                                   project=self.project)

    def test_dead_letter_queue(self):
        DLQ_name = "DLQ"
        meta = {'ttl': 3, 'grace': 3}
        self.queue_controller.create("DLQ", project=self.project)
        # Set dead letter queeu metadata
        metadata = {"_max_claim_count": 2,
                    "_dead_letter_queue": DLQ_name,
                    "_dead_letter_queue_messages_ttl": 9999}
        self.queue_controller.set_metadata(self.queue_name,
                                           metadata,
                                           project=self.project)

        new_messages = [{'ttl': 3600, 'body': {"key": "value"}}]

        self.message_controller.post(self.queue_name, new_messages,
                                     client_uuid=str(uuid.uuid1()),
                                     project=self.project)

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)
        self.assertIsNotNone(claim_id)
        self.assertEqual(1, len(list(messages)))
        time.sleep(5)
        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)
        self.assertIsNotNone(claim_id)
        messages = list(messages)
        self.assertEqual(1, len(messages))
        time.sleep(5)
        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)
        self.assertIsNone(claim_id)
        self.assertEqual(0, len(list(messages)))

        DLQ_messages = self.message_controller.list(DLQ_name,
                                                    project=self.project,
                                                    include_claimed=True)
        expected_msg = list(next(DLQ_messages))[0]
        self.assertEqual(9999, expected_msg["ttl"])
        self.assertEqual({"key": "value"}, expected_msg["body"])


@ddt.ddt
class SubscriptionControllerTest(ControllerBaseTest):
    """Subscriptions Controller base tests.

    """
    queue_name = 'test_queue'
    controller_base_class = storage.Subscription

    def setUp(self):
        super(SubscriptionControllerTest, self).setUp()
        self.subscription_controller = self.driver.subscription_controller
        self.queue_controller = self.driver.queue_controller

        self.source = self.queue_name
        self.subscriber = 'http://trigger.me'
        self.ttl = 600
        self.options = {'uri': 'http://fake.com'}

    def tearDown(self):
        self.queue_controller.delete(self.queue_name, project=self.project)
        super(SubscriptionControllerTest, self).tearDown()

    # NOTE(Eva-i): this method helps to test cases when the queue is
    # pre-created and when it's not.
    def _precreate_queue(self, precreate_queue):
        if precreate_queue:
            # Let's create a queue as the source of subscription
            self.queue_controller.create(self.queue_name, project=self.project)

    @ddt.data(True, False)
    def test_list(self, precreate_queue):
        self._precreate_queue(precreate_queue)
        for s in six.moves.xrange(15):
            subscriber = 'http://fake_{0}'.format(s)
            s_id = self.subscription_controller.create(
                self.source,
                subscriber,
                self.ttl,
                self.options,
                project=self.project)
            self.addCleanup(self.subscription_controller.delete, self.source,
                            s_id, self.project)

        added_age = 1
        time.sleep(added_age)
        interaction = self.subscription_controller.list(self.source,
                                                        project=self.project)
        subscriptions = list(next(interaction))

        self.assertTrue(all(map(lambda s:
                                'source' in s and 'subscriber' in s,
                                subscriptions)))
        self.assertEqual(10, len(subscriptions))
        self.assertLessEqual(added_age, math.ceil(subscriptions[2]['age']))

        interaction = (self.subscription_controller.list(self.source,
                                                         project=self.project,
                       marker=next(interaction)))
        subscriptions = list(next(interaction))

        self.assertTrue(all(map(lambda s:
                                'source' in s and 'subscriber' in s,
                                subscriptions)))
        self.assertEqual(5, len(subscriptions))

    def test_small_list(self):
        subscriber = 'http://fake'
        s_id = self.subscription_controller.create(
            self.source,
            subscriber,
            self.ttl,
            self.options,
            project=self.project)
        self.addCleanup(self.subscription_controller.delete, self.source,
                        s_id, self.project)

        interaction = self.subscription_controller.list(self.source,
                                                        project=self.project)
        subscriptions = list(next(interaction))
        marker = next(interaction)

        self.assertEqual(1, len(subscriptions))

        interaction = (self.subscription_controller.list(self.source,
                                                         project=self.project,
                       marker=marker))
        subscriptions = list(next(interaction))

        self.assertEqual([], subscriptions)

    @ddt.data(True, False)
    def test_get_raises_if_subscription_does_not_exist(self, precreate_queue):
        self._precreate_queue(precreate_queue)
        self.assertRaises(errors.SubscriptionDoesNotExist,
                          self.subscription_controller.get,
                          self.queue_name,
                          'notexists',
                          project=self.project)

    @ddt.data(True, False)
    def test_lifecycle(self, precreate_queue):
        self._precreate_queue(precreate_queue)
        s_id = self.subscription_controller.create(self.source,
                                                   self.subscriber,
                                                   self.ttl,
                                                   self.options,
                                                   project=self.project)
        added_age = 2
        time.sleep(added_age)
        subscription = self.subscription_controller.get(self.queue_name,
                                                        s_id,
                                                        self.project)

        self.assertEqual(self.source, subscription['source'])
        self.assertEqual(self.subscriber, subscription['subscriber'])
        self.assertEqual(self.ttl, subscription['ttl'])
        self.assertEqual(self.options, subscription['options'])
        self.assertLessEqual(added_age, math.ceil(subscription['age']))

        exist = self.subscription_controller.exists(self.queue_name,
                                                    s_id,
                                                    self.project)

        self.assertTrue(exist)

        self.subscription_controller.update(self.queue_name,
                                            s_id,
                                            project=self.project,
                                            subscriber='http://a.com',
                                            options={'funny': 'no'}
                                            )

        updated = self.subscription_controller.get(self.queue_name,
                                                   s_id,
                                                   self.project)

        self.assertEqual('http://a.com', updated['subscriber'])
        self.assertEqual({'funny': 'no'}, updated['options'])

        self.subscription_controller.delete(self.queue_name,
                                            s_id, project=self.project)
        self.assertRaises(errors.SubscriptionDoesNotExist,
                          self.subscription_controller.get,
                          self.queue_name, s_id)

    @ddt.data(True, False)
    def test_create_existed(self, precreate_queue):
        self._precreate_queue(precreate_queue)
        s_id = self.subscription_controller.create(
            self.source,
            self.subscriber,
            self.ttl,
            self.options,
            project=self.project)
        self.addCleanup(self.subscription_controller.delete, self.source, s_id,
                        self.project)
        self.assertIsNotNone(s_id)

        s_id = self.subscription_controller.create(self.source,
                                                   self.subscriber,
                                                   self.ttl,
                                                   self.options,
                                                   project=self.project)
        self.assertIsNone(s_id)

    def test_get_update_delete_on_non_existing_queue(self):
        self._precreate_queue(precreate_queue=True)
        s_id = self.subscription_controller.create(
            self.source,
            self.subscriber,
            self.ttl,
            self.options,
            project=self.project)
        self.addCleanup(self.subscription_controller.delete, self.source, s_id,
                        self.project)
        self.assertIsNotNone(s_id)
        non_existing_queue = "fake_name"
        # get
        self.assertRaises(errors.SubscriptionDoesNotExist,
                          self.subscription_controller.get,
                          non_existing_queue, s_id, project=self.project)
        # update
        body = {
            "subscriber": self.subscriber,
            "ttl": self.ttl,
            "options": self.options
        }
        self.assertRaises(errors.SubscriptionDoesNotExist,
                          self.subscription_controller.update,
                          non_existing_queue, s_id, project=self.project,
                          **body)
        # delete
        self.subscription_controller.delete(non_existing_queue, s_id,
                                            project=self.project)
        s_id = self.subscription_controller.get(self.queue_name, s_id,
                                                project=self.project)
        self.assertIsNotNone(s_id)

    def test_nonexist_source(self):
        try:
            s_id = self.subscription_controller.create('fake_queue_name',
                                                       self.subscriber,
                                                       self.ttl,
                                                       self.options,
                                                       self.project)
        except Exception:
            self.fail("Subscription controller should not raise an exception "
                      "in case of non-existing queue.")
        self.addCleanup(self.subscription_controller.delete, 'fake_queue_name',
                        s_id, self.project)

    @ddt.data(True, False)
    def test_update_raises_if_try_to_update_to_existing_subscription(
            self,
            precreate_queue):
        self._precreate_queue(precreate_queue)
        # create two subscriptions: fake_0 and fake_1
        ids = []
        for s in six.moves.xrange(2):
            subscriber = 'http://fake_{0}'.format(s)
            s_id = self.subscription_controller.create(
                self.source,
                subscriber,
                self.ttl,
                self.options,
                project=self.project)
            self.addCleanup(self.subscription_controller.delete, self.source,
                            s_id, self.project)
            ids.append(s_id)
        # update fake_0 to fake_2, success
        update_fields = {
            'subscriber': 'http://fake_2'
        }
        self.subscription_controller.update(self.queue_name,
                                            ids[0],
                                            project=self.project,
                                            **update_fields)
        # update fake_1 to fake_2, raise error
        self.assertRaises(errors.SubscriptionAlreadyExists,
                          self.subscription_controller.update,
                          self.queue_name,
                          ids[1],
                          project=self.project,
                          **update_fields)

    @ddt.data(True, False)
    def test_update_raises_if_subscription_does_not_exist(self,
                                                          precreate_queue):
        self._precreate_queue(precreate_queue)
        update_fields = {
            'subscriber': 'http://fake'
        }
        self.assertRaises(errors.SubscriptionDoesNotExist,
                          self.subscription_controller.update,
                          self.queue_name,
                          'notexists',
                          project=self.project,
                          **update_fields)

    def test_confirm(self):
        s_id = self.subscription_controller.create(self.source,
                                                   self.subscriber,
                                                   self.ttl,
                                                   self.options,
                                                   project=self.project)
        self.addCleanup(self.subscription_controller.delete, self.source,
                        s_id, self.project)
        subscription = self.subscription_controller.get(self.source, s_id,
                                                        project=self.project)
        self.assertFalse(subscription['confirmed'])

        self.subscription_controller.confirm(self.source, s_id,
                                             project=self.project,
                                             confirmed=True)
        subscription = self.subscription_controller.get(self.source, s_id,
                                                        project=self.project)
        self.assertTrue(subscription['confirmed'])

        self.subscription_controller.confirm(self.source, s_id,
                                             project=self.project,
                                             confirmed=False)
        subscription = self.subscription_controller.get(self.source, s_id,
                                                        project=self.project)
        self.assertFalse(subscription['confirmed'])

    def test_confirm_with_nonexist_subscription(self):
        s_id = 'fake-id'
        self.assertRaises(errors.SubscriptionDoesNotExist,
                          self.subscription_controller.confirm,
                          self.source, s_id, project=self.project,
                          confirmed=True
                          )


class PoolsControllerTest(ControllerBaseTest):
    """Pools Controller base tests.

    NOTE(flaper87): Implementations of this class should
    override the tearDown method in order
    to clean up storage's state.
    """
    controller_base_class = storage.PoolsBase

    def setUp(self):
        super(PoolsControllerTest, self).setUp()
        self.pools_controller = self.driver.pools_controller

        # Let's create one pool
        self.pool = str(uuid.uuid1())
        self.pool_group = str(uuid.uuid1())
        self.pools_controller.create(self.pool, 100, 'localhost',
                                     group=self.pool_group, options={})

        self.flavors_controller = self.driver.flavors_controller

    def tearDown(self):
        self.pools_controller.drop_all()
        super(PoolsControllerTest, self).tearDown()

    def test_create_succeeds(self):
        self.pools_controller.create(str(uuid.uuid1()),
                                     100, 'localhost:13124',
                                     options={})

    def test_create_replaces_on_duplicate_insert(self):
        name = str(uuid.uuid1())
        self.pools_controller.create(name,
                                     100, 'localhost:76553',
                                     options={})
        self.pools_controller.create(name,
                                     111, 'localhost:758353',
                                     options={})
        entry = self.pools_controller.get(name)
        self._pool_expects(entry, xname=name, xweight=111,
                           xlocation='localhost:758353')

    def _pool_expects(self, pool, xname, xweight, xlocation):
        self.assertIn('name', pool)
        self.assertEqual(xname, pool['name'])
        self.assertIn('weight', pool)
        self.assertEqual(xweight, pool['weight'])
        self.assertIn('uri', pool)
        self.assertEqual(xlocation, pool['uri'])

    def test_get_returns_expected_content(self):
        res = self.pools_controller.get(self.pool)
        self._pool_expects(res, self.pool, 100, 'localhost')
        self.assertNotIn('options', res)

    def test_detailed_get_returns_expected_content(self):
        res = self.pools_controller.get(self.pool, detailed=True)
        self.assertIn('options', res)
        self.assertEqual({}, res['options'])

    def test_get_raises_if_not_found(self):
        self.assertRaises(errors.PoolDoesNotExist,
                          self.pools_controller.get, 'notexists')

    def test_exists(self):
        self.assertTrue(self.pools_controller.exists(self.pool))
        self.assertFalse(self.pools_controller.exists('notexists'))

    def test_update_raises_assertion_error_on_bad_fields(self):
        self.assertRaises(AssertionError, self.pools_controller.update,
                          self.pool)

    def test_update_works(self):
        # NOTE(flaper87): This may fail for redis. Create
        # a dummy store for tests.
        self.pools_controller.update(self.pool, weight=101,
                                     uri='localhost3',
                                     options={'a': 1})
        res = self.pools_controller.get(self.pool, detailed=True)
        self._pool_expects(res, self.pool, 101, 'localhost3')
        self.assertEqual({'a': 1}, res['options'])

    def test_delete_works(self):
        self.pools_controller.delete(self.pool)
        self.assertFalse(self.pools_controller.exists(self.pool))

    def test_delete_nonexistent_is_silent(self):
        self.pools_controller.delete('nonexisting')

    def test_drop_all_leads_to_empty_listing(self):
        self.pools_controller.drop_all()
        cursor = self.pools_controller.list()
        pools = next(cursor)
        self.assertRaises(StopIteration, next, pools)

    def test_listing_simple(self):
        # NOTE(cpp-cabrera): base entry interferes with listing results
        self.pools_controller.delete(self.pool)

        pools = []
        marker = ''
        for i in range(15):
            n = str(uuid.uuid4())
            w = random.randint(1, 100)
            pools.append({'n': n, 'w': w, 'u': str(i)})

            # Keep the max name as marker
            if n > marker:
                marker = n

            self.pools_controller.create(n, w, str(i), options={})

        # Get the target pool
        def _pool(name):
            pool = [p for p in pools if p['n'] == name]
            self.assertEqual(1, len(pool))

            pool = pool[0]
            n = pool['n']
            w = pool['w']
            u = pool['u']

            return n, w, u

        def get_res(**kwargs):
            cursor = self.pools_controller.list(**kwargs)
            res = list(next(cursor))
            marker = next(cursor)
            # TODO(jeffrey4l): marker should exist
            self.assertTrue(marker)
            return res

        res = get_res()
        self.assertEqual(10, len(res))
        for entry in res:
            n, w, u = _pool(entry['name'])

            self._pool_expects(entry, n, w, u)
            self.assertNotIn('options', entry)

        res = get_res(limit=5)
        self.assertEqual(5, len(res))

        res = get_res(limit=0)
        self.assertEqual(15, len(res))

        next_name = marker + 'n'
        self.pools_controller.create(next_name, 123, '123', options={})
        res = get_res(marker=marker)
        self._pool_expects(res[0], next_name, 123, '123')
        self.pools_controller.delete(next_name)

        res = get_res(detailed=True)
        self.assertEqual(10, len(res))
        for entry in res:
            n, w, u = _pool(entry['name'])

            self._pool_expects(entry, n, w, u)
            self.assertIn('options', entry)
            self.assertEqual({}, entry['options'])

    def test_mismatching_capabilities(self):
        # NOTE(flaper87): This may fail for redis. Create
        # a dummy store for tests.
        with testing.expect(errors.PoolCapabilitiesMismatch):
            self.pools_controller.create(str(uuid.uuid1()),
                                         100, 'redis://localhost',
                                         group=self.pool_group,
                                         options={})


class CatalogueControllerTest(ControllerBaseTest):
    controller_base_class = storage.CatalogueBase

    def setUp(self):
        super(CatalogueControllerTest, self).setUp()
        self.controller = self.driver.catalogue_controller
        self.pool_ctrl = self.driver.pools_controller
        self.queue = six.text_type(uuid.uuid4())
        self.project = six.text_type(uuid.uuid4())

        self.pool = str(uuid.uuid1())
        self.pool_group = str(uuid.uuid1())
        self.pool_ctrl.create(self.pool, 100, 'localhost',
                              group=self.pool_group, options={})
        self.addCleanup(self.pool_ctrl.delete, self.pool)

    def tearDown(self):
        self.controller.drop_all()
        super(CatalogueControllerTest, self).tearDown()

    def _check_structure(self, entry):
        self.assertIn('queue', entry)
        self.assertIn('project', entry)
        self.assertIn('pool', entry)
        self.assertIsInstance(entry['queue'], six.text_type)
        self.assertIsInstance(entry['project'], six.text_type)
        self.assertIsInstance(entry['pool'], six.text_type)

    def _check_value(self, entry, xqueue, xproject, xpool):
        self.assertEqual(xqueue, entry['queue'])
        self.assertEqual(xproject, entry['project'])
        self.assertEqual(xpool, entry['pool'])

    def test_catalogue_entry_life_cycle(self):
        queue = self.queue
        project = self.project

        # check listing is initially empty
        for p in self.controller.list(project):
            self.fail('There should be no entries at this time')

        # create a listing, check its length
        with helpers.pool_entries(self.controller,
                                  self.pool_ctrl, 10) as expect:
            project = expect[0][0]
            xs = list(self.controller.list(project))
            self.assertEqual(10, len(xs))

        # create, check existence, delete
        with helpers.pool_entry(self.controller, project, queue, self.pool):
            self.assertTrue(self.controller.exists(project, queue))

        # verify it no longer exists
        self.assertFalse(self.controller.exists(project, queue))

        # verify it isn't listable
        self.assertEqual(0, len(list(self.controller.list(project))))

    def test_list(self):
        with helpers.pool_entries(self.controller,
                                  self.pool_ctrl, 10) as expect:
            values = zip(self.controller.list(u'_'), expect)
            for e, x in values:
                p, q, s = x
                self._check_structure(e)
                self._check_value(e, xqueue=q, xproject=p, xpool=s)

    def test_update(self):
        p2 = u'b'
        self.pool_ctrl.create(p2, 100, '127.0.0.1',
                              group=self.pool_group,
                              options={})
        self.addCleanup(self.pool_ctrl.delete, p2)

        with helpers.pool_entry(self.controller, self.project,
                                self.queue, self.pool) as expect:
            p, q, s = expect
            self.controller.update(p, q, pool=p2)
            entry = self.controller.get(p, q)
            self._check_value(entry, xqueue=q, xproject=p, xpool=p2)

    def test_update_raises_when_entry_does_not_exist(self):
        e = self.assertRaises(errors.QueueNotMapped,
                              self.controller.update,
                              'p', 'q', 'a')
        self.assertIn('queue q for project p', str(e))

    def test_get(self):
        with helpers.pool_entry(self.controller,
                                self.project,
                                self.queue, self.pool) as expect:
            p, q, s = expect
            e = self.controller.get(p, q)
            self._check_value(e, xqueue=q, xproject=p, xpool=s)

    def test_get_raises_if_does_not_exist(self):
        with helpers.pool_entry(self.controller,
                                self.project,
                                self.queue, u'a') as expect:
            p, q, _ = expect
            self.assertRaises(errors.QueueNotMapped,
                              self.controller.get,
                              p, 'non_existing')
            self.assertRaises(errors.QueueNotMapped,
                              self.controller.get,
                              'non_existing', q)
            self.assertRaises(errors.QueueNotMapped,
                              self.controller.get,
                              'non_existing', 'non_existing')

    def test_exists(self):
        with helpers.pool_entry(self.controller,
                                self.project,
                                self.queue, self.pool) as expect:
            p, q, _ = expect
            self.assertTrue(self.controller.exists(p, q))
            self.assertFalse(self.controller.exists('nada', 'not_here'))

    def test_insert(self):
        q1 = six.text_type(uuid.uuid1())
        q2 = six.text_type(uuid.uuid1())
        self.controller.insert(self.project, q1, u'a')
        self.controller.insert(self.project, q2, u'a')


class FlavorsControllerTest(ControllerBaseTest):
    """Flavors Controller base tests.

    NOTE(flaper87): Implementations of this class should
    override the tearDown method in order
    to clean up storage's state.
    """
    controller_base_class = storage.FlavorsBase

    def setUp(self):
        super(FlavorsControllerTest, self).setUp()
        self.pools_controller = self.driver.pools_controller
        self.flavors_controller = self.driver.flavors_controller

        # Let's create one pool
        self.pool = str(uuid.uuid1())
        self.pool_group = str(uuid.uuid1())
        self.pools_controller.create(self.pool, 100, 'localhost',
                                     group=self.pool_group, options={})
        self.addCleanup(self.pools_controller.delete, self.pool)

    def tearDown(self):
        self.flavors_controller.drop_all()
        super(FlavorsControllerTest, self).tearDown()

    def test_create_succeeds(self):
        self.flavors_controller.create('durable', self.pool_group,
                                       project=self.project,
                                       capabilities={})

    def _flavors_expects(self, flavor, xname, xproject, xpool):
        self.assertIn('name', flavor)
        self.assertEqual(xname, flavor['name'])
        self.assertNotIn('project', flavor)
        self.assertIn('pool_group', flavor)
        self.assertEqual(xpool, flavor['pool_group'])

    def test_create_replaces_on_duplicate_insert(self):
        name = str(uuid.uuid1())
        self.flavors_controller.create(name, self.pool_group,
                                       project=self.project,
                                       capabilities={})

        pool2 = 'another_pool'
        self.pools_controller.create(pool2, 100, 'localhost:27017',
                                     group=pool2, options={})
        self.addCleanup(self.pools_controller.delete, pool2)

        self.flavors_controller.create(name, pool2,
                                       project=self.project,
                                       capabilities={})
        entry = self.flavors_controller.get(name, project=self.project)
        self._flavors_expects(entry, name, self.project, pool2)

    def test_get_returns_expected_content(self):
        name = 'durable'
        capabilities = {'fifo': True}
        self.flavors_controller.create(name, self.pool_group,
                                       project=self.project,
                                       capabilities=capabilities)
        res = self.flavors_controller.get(name, project=self.project)
        self._flavors_expects(res, name, self.project, self.pool_group)
        self.assertNotIn('capabilities', res)

    def test_detailed_get_returns_expected_content(self):
        name = 'durable'
        capabilities = {'fifo': True}
        self.flavors_controller.create(name, self.pool_group,
                                       project=self.project,
                                       capabilities=capabilities)
        res = self.flavors_controller.get(name, project=self.project,
                                          detailed=True)
        self._flavors_expects(res, name, self.project, self.pool_group)
        self.assertIn('capabilities', res)
        self.assertEqual(capabilities, res['capabilities'])

    def test_get_raises_if_not_found(self):
        self.assertRaises(errors.FlavorDoesNotExist,
                          self.flavors_controller.get, 'notexists')

    def test_exists(self):
        self.flavors_controller.create('exists', self.pool_group,
                                       project=self.project,
                                       capabilities={})
        self.assertTrue(self.flavors_controller.exists('exists',
                                                       project=self.project))
        self.assertFalse(self.flavors_controller.exists('notexists',
                                                        project=self.project))

    def test_update_raises_assertion_error_on_bad_fields(self):
        self.assertRaises(AssertionError, self.pools_controller.update,
                          self.pool_group)

    def test_update_works(self):
        name = 'yummy'
        self.flavors_controller.create(name, self.pool_group,
                                       project=self.project,
                                       capabilities={})

        res = self.flavors_controller.get(name, project=self.project,
                                          detailed=True)

        p = 'olympic'
        pool_group = 'sports'
        self.pools_controller.create(p, 100, 'localhost2',
                                     group=pool_group, options={})
        self.addCleanup(self.pools_controller.delete, p)

        new_capabilities = {'fifo': False}
        self.flavors_controller.update(name, project=self.project,
                                       pool_group=pool_group,
                                       capabilities={'fifo': False})
        res = self.flavors_controller.get(name, project=self.project,
                                          detailed=True)
        self._flavors_expects(res, name, self.project, pool_group)
        self.assertEqual(new_capabilities, res['capabilities'])

    def test_delete_works(self):
        name = 'puke'
        self.flavors_controller.create(name, self.pool_group,
                                       project=self.project,
                                       capabilities={})
        self.flavors_controller.delete(name, project=self.project)
        self.assertFalse(self.flavors_controller.exists(name))

    def test_delete_nonexistent_is_silent(self):
        self.flavors_controller.delete('nonexisting')

    def test_drop_all_leads_to_empty_listing(self):
        self.flavors_controller.drop_all()
        cursor = self.flavors_controller.list()
        flavors = next(cursor)
        self.assertRaises(StopIteration, next, flavors)
        self.assertFalse(next(cursor))

    def test_listing_simple(self):
        name_gen = lambda i: chr(ord('A') + i)
        for i in range(15):
            pool = str(i)
            pool_group = pool
            uri = 'localhost:2701' + pool
            self.pools_controller.create(pool, 100, uri,
                                         group=pool_group, options={})
            self.addCleanup(self.pools_controller.delete, pool)

            self.flavors_controller.create(name_gen(i), project=self.project,
                                           pool_group=pool_group,
                                           capabilities={})

        def get_res(**kwargs):
            cursor = self.flavors_controller.list(project=self.project,
                                                  **kwargs)
            res = list(next(cursor))
            marker = next(cursor)
            self.assertTrue(marker)
            return res

        res = get_res()
        self.assertEqual(10, len(res))
        for i, entry in enumerate(res):
            self._flavors_expects(entry, name_gen(i), self.project, str(i))
            self.assertNotIn('capabilities', entry)

        res = get_res(limit=5)
        self.assertEqual(5, len(res))

        res = get_res(marker=name_gen(3))
        self._flavors_expects(res[0], name_gen(4), self.project, '4')

        res = get_res(detailed=True)
        self.assertEqual(10, len(res))
        for i, entry in enumerate(res):
            self._flavors_expects(entry, name_gen(i), self.project, str(i))
            self.assertIn('capabilities', entry)
            self.assertEqual({}, entry['capabilities'])


def _insert_fixtures(controller, queue_name, project=None,
                     client_uuid=None, num=4, ttl=120):
    def messages():
        for n in six.moves.xrange(num):
            yield {
                'ttl': ttl,
                'body': {
                    'event': 'Event number {0}'.format(n)
                }}

    return controller.post(queue_name, messages(),
                           project=project, client_uuid=client_uuid)

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

import datetime
import random
import time
import uuid

import ddt
import mock
from oslo.utils import timeutils
import six
from testtools import matchers

from zaqar.openstack.common.cache import cache as oslo_cache
from zaqar import storage
from zaqar.storage import errors
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

        oslo_cache.register_oslo_configs(self.conf)
        cache = oslo_cache.get_cache(self.conf.cache_url)

        pooling = 'pooling' in self.conf and self.conf.pooling
        if pooling and not self.control_driver_class:
            self.skipTest("Pooling is enabled, "
                          "but control driver class is not specified")

        if not pooling:
            self.driver = self.driver_class(self.conf, cache)
        else:
            control = self.control_driver_class(self.conf, cache)
            uri = "sqlite:///:memory:"
            for i in range(4):
                control.pools_controller.create(six.text_type(i), 100, uri)
            self.driver = self.driver_class(self.conf, cache, control)

        self._prepare_conf()

        self.addCleanup(self._purge_databases)

        if not pooling:
            self.controller = self.controller_class(self.driver)
        else:
            self.controller = self.controller_class(self.driver._pool_catalog)

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
        self.queue_controller = self.driver.queue_controller
        self.message_controller = self.driver.message_controller
        self.claim_controller = self.driver.claim_controller

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

        self.assertEqual(all(map(lambda queue:
                                 'name' in queue and
                                 'metadata' in queue, queues)), True)
        self.assertEqual(len(queues), 10)

        interaction = self.controller.list(project=project,
                                           marker=next(interaction))
        queues = list(next(interaction))

        self.assertEqual(all(map(lambda queue:
                                 'name' in queue and
                                 'metadata' not in queue, queues)), True)
        self.assertEqual(len(queues), 5)

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
        self.assertEqual(queue['name'], 'test')

        # Test queue metadata retrieval
        metadata = self.controller.get('test', project=self.project)
        self.assertEqual(metadata['meta'], 'test_meta')

        # Touching an existing queue does not affect metadata
        created = self.controller.create('test', project=self.project)
        self.assertFalse(created)

        metadata = self.controller.get('test', project=self.project)
        self.assertEqual(metadata['meta'], 'test_meta')

        client_uuid = uuid.uuid4()

        # Test queue statistic
        _insert_fixtures(self.message_controller, 'test',
                         project=self.project, client_uuid=client_uuid,
                         num=6)

        # NOTE(kgriffs): We can't get around doing this, because
        # we don't know how the storage drive may be calculating
        # message timestamps (and may not be monkey-patchable).
        time.sleep(1.2)

        _insert_fixtures(self.message_controller, 'test',
                         project=self.project, client_uuid=client_uuid,
                         num=6)

        stats = self.controller.stats('test', project=self.project)
        message_stats = stats['messages']

        self.assertEqual(message_stats['free'], 12)
        self.assertEqual(message_stats['claimed'], 0)
        self.assertEqual(message_stats['total'], 12)

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

        # Test queue deletion
        self.controller.delete('test', project=self.project)

        # Test queue existence
        self.assertFalse(self.controller.exists('test', project=self.project))

    def test_stats_for_empty_queue(self):
        self.addCleanup(self.controller.delete, 'test', project=self.project)
        created = self.controller.create('test', project=self.project)
        self.assertTrue(created)

        stats = self.controller.stats('test', project=self.project)
        message_stats = stats['messages']

        self.assertEqual(message_stats['free'], 0)
        self.assertEqual(message_stats['claimed'], 0)
        self.assertEqual(message_stats['total'], 0)

        self.assertNotIn('newest', message_stats)
        self.assertNotIn('oldest', message_stats)

    def test_queue_count_on_bulk_delete(self):
        self.addCleanup(self.controller.delete, 'test-queue',
                        project=self.project)
        queue_name = 'test-queue'
        client_uuid = uuid.uuid4()

        created = self.controller.create(queue_name, project=self.project)
        self.assertTrue(created)

        # Create 10 messages.
        msg_keys = _insert_fixtures(self.message_controller, queue_name,
                                    project=self.project,
                                    client_uuid=client_uuid, num=10)

        stats = self.controller.stats(queue_name,
                                      self.project)['messages']
        self.assertEqual(stats['total'], 10)

        # Delete 5 messages
        self.message_controller.bulk_delete(queue_name, msg_keys[0:5],
                                            self.project)

        stats = self.controller.stats(queue_name,
                                      self.project)['messages']
        self.assertEqual(stats['total'], 5)

    def test_queue_count_on_bulk_delete_with_invalid_id(self):
        self.addCleanup(self.controller.delete, 'test-queue',
                        project=self.project)
        queue_name = 'test-queue'
        client_uuid = uuid.uuid4()

        created = self.controller.create(queue_name, project=self.project)
        self.assertTrue(created)

        # Create 10 messages.
        msg_keys = _insert_fixtures(self.message_controller, queue_name,
                                    project=self.project,
                                    client_uuid=client_uuid, num=10)

        stats = self.controller.stats(queue_name,
                                      self.project)['messages']
        self.assertEqual(stats['total'], 10)

        # Delete 5 messages
        self.message_controller.bulk_delete(queue_name,
                                            msg_keys[0:5] + ['invalid'],
                                            self.project)

        stats = self.controller.stats(queue_name,
                                      self.project)['messages']
        self.assertEqual(stats['total'], 5)

    def test_queue_count_on_delete(self):
        self.addCleanup(self.controller.delete, 'test-queue',
                        project=self.project)
        queue_name = 'test-queue'
        client_uuid = uuid.uuid4()

        created = self.controller.create(queue_name, project=self.project)
        self.assertTrue(created)

        # Create 10 messages.
        msg_keys = _insert_fixtures(self.message_controller, queue_name,
                                    project=self.project,
                                    client_uuid=client_uuid, num=10)

        stats = self.controller.stats(queue_name,
                                      self.project)['messages']
        self.assertEqual(stats['total'], 10)

        # Delete 1 message
        self.message_controller.delete(queue_name, msg_keys[0],
                                       self.project)
        stats = self.controller.stats(queue_name,
                                      self.project)['messages']
        self.assertEqual(stats['total'], 9)

    def test_queue_count_on_claim_delete(self):
        self.addCleanup(self.controller.delete, 'test-queue',
                        project=self.project)
        queue_name = 'test-queue'
        client_uuid = uuid.uuid4()

        created = self.controller.create(queue_name, project=self.project)
        self.assertTrue(created)

        # Create 15 messages.
        msg_keys = _insert_fixtures(self.message_controller, queue_name,
                                    project=self.project,
                                    client_uuid=client_uuid, num=15)

        stats = self.controller.stats(queue_name,
                                      self.project)['messages']
        self.assertEqual(stats['total'], 15)

        metadata = {'ttl': 120, 'grace': 60}
        # Claim 10 messages
        claim_id, _ = self.claim_controller.create(queue_name, metadata,
                                                   self.project)

        stats = self.controller.stats(queue_name,
                                      self.project)['messages']
        self.assertEqual(stats['claimed'], 10)

        # Delete one message and ensure stats are updated even
        # thought the claim itself has not been deleted.
        self.message_controller.delete(queue_name, msg_keys[0],
                                       self.project, claim_id)
        stats = self.controller.stats(queue_name,
                                      self.project)['messages']
        self.assertEqual(stats['total'], 14)
        self.assertEqual(stats['claimed'], 9)
        self.assertEqual(stats['free'], 5)

        # Same thing but use bulk_delete interface
        self.message_controller.bulk_delete(queue_name, msg_keys[1:3],
                                            self.project)
        stats = self.controller.stats(queue_name,
                                      self.project)['messages']
        self.assertEqual(stats['total'], 12)
        self.assertEqual(stats['claimed'], 7)
        self.assertEqual(stats['free'], 5)

        # Delete the claim
        self.claim_controller.delete(queue_name, claim_id,
                                     self.project)
        stats = self.controller.stats(queue_name,
                                      self.project)['messages']

        self.assertEqual(stats['claimed'], 0)


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
        self.queue_controller = self.driver.queue_controller
        self.claim_controller = self.driver.claim_controller
        self.queue_controller.create(self.queue_name, project=self.project)

    def tearDown(self):
        self.queue_controller.delete(self.queue_name, project=self.project)
        super(MessageControllerTest, self).tearDown()

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
        self.assertEqual(len(created), 1)
        message_id = created[0]

        # Test Message Get
        message_out = self.controller.get(queue_name, message_id,
                                          project=self.project)
        self.assertEqual(set(message_out), set(('id', 'body', 'ttl', 'age',
                                                'claim_id')))
        self.assertEqual(message_out['id'], message_id)
        self.assertEqual(message_out['body'], message['body'])
        self.assertEqual(message_out['ttl'], message['ttl'])

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
            self.assertEqual(len(msgs), expected)
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
            self.assertEqual(set(message),
                             set(('id', 'body', 'ttl', 'age', 'claim_id')))
            self.assertEqual(message['body'], idx)

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
        with testing.expect(errors.NotPermitted):
            self.controller.delete(self.queue_name, msg2['id'],
                                   project=self.project,
                                   claim=cid)

    @testing.is_slow(condition=lambda self: self.gc_interval > 1)
    def test_expired_messages(self):
        messages = [{'body': 3.14, 'ttl': 0}, {'body': 0.618, 'ttl': 600}]
        client_uuid = uuid.uuid4()

        [msgid_expired, msgid] = self.controller.post(self.queue_name,
                                                      messages,
                                                      project=self.project,
                                                      client_uuid=client_uuid)

        # NOTE(kgriffs): Allow for automatic GC of claims, messages
        time.sleep(self.gc_interval)

        # NOTE(kgriffs): Some drivers require a manual GC to be
        # triggered to clean up claims and messages.
        self.driver.gc()

        with testing.expect(errors.DoesNotExist):
            self.controller.get(self.queue_name, msgid_expired,
                                project=self.project)

        stats = self.queue_controller.stats(self.queue_name,
                                            project=self.project)

        self.assertEqual(stats['messages']['free'], 1)

        # Make sure expired messages not return when listing
        interaction = self.controller.list(self.queue_name,
                                           project=self.project)

        messages = list(next(interaction))
        self.assertEqual(len(messages), 1)
        self.assertEqual(msgid, messages[0]['id'])

        # Make sure expired messages not return when popping
        messages = self.controller.pop(self.queue_name,
                                       limit=10,
                                       project=self.project)
        self.assertEqual(len(messages), 1)
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

        self.assertEqual(messages, [])

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
        self.assertEqual(msg_asc['id'], msgid_first)

        msg_desc = self.controller.first(self.queue_name,
                                         self.project,
                                         -1)
        self.assertEqual(msg_desc['id'], msgid_last)

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

        self.assertEqual(len(popped_messages), 1)


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
        self.queue_controller = self.driver.queue_controller
        self.message_controller = self.driver.message_controller
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
        self.assertEqual(len(messages), 15)

        # Ensure Queue stats
        countof = self.queue_controller.stats(self.queue_name,
                                              project=self.project)
        self.assertEqual(countof['messages']['claimed'], 15)
        self.assertEqual(countof['messages']['free'], 5)
        self.assertEqual(countof['messages']['total'], 20)

        # Make sure get works
        claim, messages2 = self.controller.get(self.queue_name, claim_id,
                                               project=self.project)

        messages2 = list(messages2)
        self.assertEqual(len(messages2), 15)
        self.assertEqual(messages, messages2)
        self.assertEqual(claim['ttl'], 70)
        self.assertEqual(claim['id'], claim_id)

        new_meta = {'ttl': 100, 'grace': 60}
        self.controller.update(self.queue_name, claim_id,
                               new_meta, project=self.project)

        # Make sure update works
        claim, messages2 = self.controller.get(self.queue_name, claim_id,
                                               project=self.project)

        messages2 = list(messages2)
        self.assertEqual(len(messages2), 15)

        # TODO(zyuan): Add some tests to ensure the ttl is
        # extended/not-extended.
        for msg1, msg2 in zip(messages, messages2):
            self.assertEqual(msg1['body'], msg2['body'])

        self.assertEqual(claim['ttl'], new_meta['ttl'])
        self.assertEqual(claim['id'], claim_id)

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
            self.assertEqual(num_claimed,
                             storage.DEFAULT_MESSAGES_PER_CLAIM)

            total_claimed += num_claimed

        self.assertEqual(total_claimed, num_messages)

    def test_extend_lifetime(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid=uuid.uuid4(),
                         num=20, ttl=120)

        meta = {'ttl': 777, 'grace': 0}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEqual(message['ttl'], 777)

    def test_extend_lifetime_with_grace_1(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid=uuid.uuid4(),
                         num=20, ttl=120)

        meta = {'ttl': 777, 'grace': 23}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEqual(message['ttl'], 800)

    def test_extend_lifetime_with_grace_2(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid=uuid.uuid4(),
                         num=20, ttl=120)

        meta = {'ttl': 121, 'grace': 22}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEqual(message['ttl'], 143)

    def test_do_not_extend_lifetime(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid=uuid.uuid4(),
                         num=20, ttl=120)

        # Choose a ttl that is less than the message's current TTL
        meta = {'ttl': 60, 'grace': 30}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEqual(message['ttl'], 120)

    def test_expired_claim(self):
        meta = {'ttl': 0, 'grace': 60}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

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
        timeutils_utcnow = 'oslo.utils.timeutils.utcnow_ts'

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

    def tearDown(self):
        self.pools_controller.drop_all()
        super(PoolsControllerTest, self).tearDown()

    def test_create_succeeds(self):
        self.pools_controller.create(str(uuid.uuid1()),
                                     100, 'localhost',
                                     options={})

    def test_create_replaces_on_duplicate_insert(self):
        name = str(uuid.uuid1())
        self.pools_controller.create(name,
                                     100, 'localhost',
                                     options={})
        self.pools_controller.create(name,
                                     111, 'localhost2',
                                     options={})
        entry = self.pools_controller.get(name)
        self._pool_expects(entry, xname=name, xweight=111,
                           xlocation='localhost2')

    def _pool_expects(self, pool, xname, xweight, xlocation):
        self.assertIn('name', pool)
        self.assertEqual(pool['name'], xname)
        self.assertIn('weight', pool)
        self.assertEqual(pool['weight'], xweight)
        self.assertIn('uri', pool)
        self.assertEqual(pool['uri'], xlocation)

    def test_get_returns_expected_content(self):
        res = self.pools_controller.get(self.pool)
        self._pool_expects(res, self.pool, 100, 'localhost')
        self.assertNotIn('options', res)

    def test_detailed_get_returns_expected_content(self):
        res = self.pools_controller.get(self.pool, detailed=True)
        self.assertIn('options', res)
        self.assertEqual(res['options'], {})

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
        self.pools_controller.update(self.pool, weight=101,
                                     uri='redis://localhost',
                                     options={'a': 1})
        res = self.pools_controller.get(self.pool, detailed=True)
        self._pool_expects(res, self.pool, 101, 'redis://localhost')
        self.assertEqual(res['options'], {'a': 1})

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
            self.assertEqual(len(pool), 1)

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
        self.assertEqual(len(res), 10)
        for entry in res:
            n, w, u = _pool(entry['name'])

            self._pool_expects(entry, n, w, u)
            self.assertNotIn('options', entry)

        res = get_res(limit=5)
        self.assertEqual(len(res), 5)

        res = get_res(limit=0)
        self.assertEqual(len(res), 15)

        next_name = marker + 'n'
        self.pools_controller.create(next_name, 123, '123', options={})
        res = get_res(marker=marker)
        self._pool_expects(res[0], next_name, 123, '123')
        self.pools_controller.delete(next_name)

        res = get_res(detailed=True)
        self.assertEqual(len(res), 10)
        for entry in res:
            n, w, u = _pool(entry['name'])

            self._pool_expects(entry, n, w, u)
            self.assertIn('options', entry)
            self.assertEqual(entry['options'], {})


class CatalogueControllerTest(ControllerBaseTest):
    controller_base_class = storage.CatalogueBase

    def setUp(self):
        super(CatalogueControllerTest, self).setUp()
        self.controller = self.driver.catalogue_controller
        self.queue = six.text_type(uuid.uuid1())
        self.project = six.text_type(uuid.uuid1())

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
        self.assertEqual(entry['queue'], xqueue)
        self.assertEqual(entry['project'], xproject)
        self.assertEqual(entry['pool'], xpool)

    def test_catalogue_entry_life_cycle(self):
        queue = self.queue
        project = self.project

        # check listing is initially empty
        for p in self.controller.list(project):
            self.fail('There should be no entries at this time')

        # create a listing, check its length
        with helpers.pool_entries(self.controller, 10) as expect:
            project = expect[0][0]
            xs = list(self.controller.list(project))
            self.assertEqual(len(xs), 10)

        # create, check existence, delete
        with helpers.pool_entry(self.controller, project, queue, u'a'):
            self.assertTrue(self.controller.exists(project, queue))

        # verify it no longer exists
        self.assertFalse(self.controller.exists(project, queue))

        # verify it isn't listable
        self.assertEqual(len(list(self.controller.list(project))), 0)

    def test_list(self):
        with helpers.pool_entries(self.controller, 10) as expect:
            values = zip(self.controller.list(u'_'), expect)
            for e, x in values:
                p, q, s = x
                self._check_structure(e)
                self._check_value(e, xqueue=q, xproject=p, xpool=s)

    def test_update(self):
        with helpers.pool_entry(self.controller, self.project,
                                self.queue, u'a') as expect:
            p, q, s = expect
            self.controller.update(p, q, pool=u'b')
            entry = self.controller.get(p, q)
            self._check_value(entry, xqueue=q, xproject=p, xpool=u'b')

    def test_update_raises_when_entry_does_not_exist(self):
        e = self.assertRaises(errors.QueueNotMapped,
                              self.controller.update,
                              'p', 'q', 'a')
        self.assertIn('queue q for project p', str(e))

    def test_get(self):
        with helpers.pool_entry(self.controller,
                                self.project,
                                self.queue, u'a') as expect:
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
                                self.queue, u'a') as expect:
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
        self.assertEqual(flavor['name'], xname)
        self.assertIn('project', flavor)
        self.assertEqual(flavor['project'], xproject)
        self.assertIn('pool', flavor)
        self.assertEqual(flavor['pool'], xpool)

    def test_create_replaces_on_duplicate_insert(self):
        name = str(uuid.uuid1())
        self.flavors_controller.create(name, self.pool_group,
                                       project=self.project,
                                       capabilities={})

        pool2 = 'another_pool'
        self.pools_controller.create(pool2, 100, 'localhost',
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
        self.assertEqual(res['capabilities'], capabilities)

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

        new_capabilities = {'fifo': False}
        self.flavors_controller.update(name, project=self.project,
                                       pool='olympic',
                                       capabilities={'fifo': False})
        res = self.flavors_controller.get(name, project=self.project,
                                          detailed=True)
        self._flavors_expects(res, name, self.project, 'olympic')
        self.assertEqual(res['capabilities'], new_capabilities)

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
            self.pools_controller.create(pool, 100, 'localhost',
                                         group=pool, options={})
            self.addCleanup(self.pools_controller.delete, pool)

            self.flavors_controller.create(name_gen(i), project=self.project,
                                           pool=pool, capabilities={})

        def get_res(**kwargs):
            cursor = self.flavors_controller.list(project=self.project,
                                                  **kwargs)
            res = list(next(cursor))
            marker = next(cursor)
            self.assertTrue(marker)
            return res

        res = get_res()
        self.assertEqual(len(res), 10)
        for i, entry in enumerate(res):
            self._flavors_expects(entry, name_gen(i), self.project, str(i))
            self.assertNotIn('capabilities', entry)

        res = get_res(limit=5)
        self.assertEqual(len(res), 5)

        res = get_res(marker=name_gen(3))
        self._flavors_expects(res[0], name_gen(4), self.project, '4')

        res = get_res(detailed=True)
        self.assertEqual(len(res), 10)
        for i, entry in enumerate(res):
            self._flavors_expects(entry, name_gen(i), self.project, str(i))
            self.assertIn('capabilities', entry)
            self.assertEqual(entry['capabilities'], {})


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

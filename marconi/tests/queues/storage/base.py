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
import time
import uuid

import ddt
import six
from testtools import matchers

from marconi.common.cache import cache as oslo_cache
from marconi.openstack.common import timeutils
from marconi.queues import storage
from marconi.queues.storage import errors
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
                              self.controller_class,
                              self.controller_base_class))

        cache = oslo_cache.get_cache(self.conf)
        self.driver = self.driver_class(self.conf, cache)
        self._prepare_conf()

        self.addCleanup(self._purge_databases)

        self.controller = self.controller_class(self.driver)

    def _prepare_conf(self):
        """Prepare the conf before running tests

        Classes overriding this method, must use
        the `self.conf` instance and alter its state.
        """

    def _purge_databases(self):
        """Override to clean databases."""

    def tearDown(self):
        timeutils.clear_time_override()
        super(ControllerBaseTest, self).tearDown()


@ddt.ddt
class QueueControllerTest(ControllerBaseTest):
    """Queue Controller base tests."""
    controller_base_class = storage.QueueBase

    def setUp(self):
        super(QueueControllerTest, self).setUp()
        self.message_controller = self.driver.message_controller
        self.claim_controller = self.driver.claim_controller

    @ddt.data(None, ControllerBaseTest.project)
    def test_list(self, project):
        # NOTE(kgriffs): Ensure we mix global and scoped queues
        # in order to verify that queue records are exluded that
        # are not at the same level.
        project_alt = self.project if project is None else None

        num = 15
        for queue in xrange(num):
            self.controller.create(str(queue), project=project)
            self.controller.create(str(queue), project=project_alt)

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
        created = self.controller.create('test', project=self.project)
        self.assertTrue(created)

        # Test queue existence
        self.assertTrue(self.controller.exists('test', project=self.project))

        # Test queue retrieval
        interaction = self.controller.list(project=self.project)
        queue = list(next(interaction))[0]
        self.assertEqual(queue['name'], 'test')

        # Test queue metadata retrieval
        metadata = self.controller.get_metadata('test', project=self.project)
        self.assertEqual(metadata, {})

        # Test queue update
        created = self.controller.set_metadata('test', project=self.project,
                                               metadata=dict(meta='test_meta'))

        metadata = self.controller.get_metadata('test', project=self.project)
        self.assertEqual(metadata['meta'], 'test_meta')

        # Touching an existing queue does not affect metadata
        created = self.controller.create('test', project=self.project)
        self.assertFalse(created)

        metadata = self.controller.get_metadata('test', project=self.project)
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

        # Test DoesNotExist exception
        with testing.expect(storage.errors.DoesNotExist):
            self.controller.get_metadata('test', project=self.project)

        with testing.expect(storage.errors.DoesNotExist):
            self.controller.set_metadata('test', '{}', project=self.project)

    def test_stats_for_empty_queue(self):
        created = self.controller.create('test', project=self.project)
        self.assertTrue(created)

        stats = self.controller.stats('test', project=self.project)
        message_stats = stats['messages']

        self.assertEqual(message_stats['free'], 0)
        self.assertEqual(message_stats['claimed'], 0)
        self.assertEqual(message_stats['total'], 0)

        self.assertNotIn('newest', message_stats)
        self.assertNotIn('oldest', message_stats)


class MessageControllerTest(ControllerBaseTest):
    """Message Controller base tests.

    NOTE(flaper87): Implementations of this class should
    override the tearDown method in order
    to clean up storage's state.
    """
    queue_name = 'test_queue'
    controller_base_class = storage.MessageBase

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

        messages = [
            {
                'ttl': 60,
                'body': {
                    'event': 'BackupStarted',
                    'backupId': 'c378813c-3f0b-11e2-ad92-7823d2b0f3ce'
                }
            },
        ]

        # Test Message Creation
        created = list(self.controller.post(queue_name, messages,
                                            project=self.project,
                                            client_uuid=uuid.uuid4()))
        self.assertEqual(len(created), 1)

        # Test Message Get
        self.controller.get(queue_name, created[0], project=self.project)

        # Test Message Deletion
        self.controller.delete(queue_name, created[0], project=self.project)

        # Test does not exist
        with testing.expect(storage.errors.DoesNotExist):
            self.controller.get(queue_name, created[0], project=self.project)

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
        with testing.expect(storage.errors.NotPermitted):
            self.controller.delete(self.queue_name, msg1['id'],
                                   project=self.project,
                                   claim=another_cid)

        # Make sure a message can be deleted with a claim
        self.controller.delete(self.queue_name, msg1['id'],
                               project=self.project,
                               claim=cid)

        with testing.expect(storage.errors.DoesNotExist):
            self.controller.get(self.queue_name, msg1['id'],
                                project=self.project)

        # Make sure such a deletion is idempotent
        self.controller.delete(self.queue_name, msg1['id'],
                               project=self.project,
                               claim=cid)

        # A non-existing claim does not ensure the message deletion
        self.claim_controller.delete(self.queue_name, cid,
                                     project=self.project)

        with testing.expect(storage.errors.NotPermitted):
            self.controller.delete(self.queue_name, msg2['id'],
                                   project=self.project,
                                   claim=cid)

    @testing.is_slow(condition=lambda self: self.gc_interval != 0)
    def test_expired_messages(self):
        messages = [{'body': 3.14, 'ttl': 0}]
        client_uuid = uuid.uuid4()

        [msgid] = self.controller.post(self.queue_name, messages,
                                       project=self.project,
                                       client_uuid=client_uuid)

        [msgid] = self.controller.post(self.queue_name, messages,
                                       project=self.project,
                                       client_uuid=client_uuid)

        time.sleep(self.gc_interval)

        with testing.expect(storage.errors.DoesNotExist):
            self.controller.get(self.queue_name, msgid,
                                project=self.project)

        stats = self.queue_controller.stats(self.queue_name,
                                            project=self.project)

        self.assertEqual(stats['messages']['free'], 0)

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


class ClaimControllerTest(ControllerBaseTest):
    """Claim Controller base tests.

    NOTE(flaper87): Implementations of this class should
    override the tearDown method in order
    to clean up storage's state.
    """
    queue_name = 'test_queue'
    controller_base_class = storage.ClaimBase

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

        self.assertEqual(claim['ttl'], 100)
        self.assertEqual(claim['id'], claim_id)

        # Make sure delete works
        self.controller.delete(self.queue_name, claim_id,
                               project=self.project)

        self.assertRaises(storage.errors.ClaimDoesNotExist,
                          self.controller.get, self.queue_name,
                          claim_id, project=self.project)

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

        # Although ttl is less than the message's TTL, the grace
        # period puts it just over the edge.
        meta = {'ttl': 100, 'grace': 22}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEqual(message['ttl'], 122)

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

        with testing.expect(storage.errors.DoesNotExist):
            self.controller.get(self.queue_name, claim_id,
                                project=self.project)

        with testing.expect(storage.errors.DoesNotExist):
            self.controller.update(self.queue_name, claim_id,
                                   meta, project=self.project)

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


class ShardsControllerTest(ControllerBaseTest):
    """Shards Controller base tests.

    NOTE(flaper87): Implementations of this class should
    override the tearDown method in order
    to clean up storage's state.
    """
    controller_base_class = storage.ShardsBase

    def setUp(self):
        super(ShardsControllerTest, self).setUp()
        self.shards_controller = self.driver.shards_controller

        # Let's create one shard
        self.shard = str(uuid.uuid1())
        self.shards_controller.create(self.shard, 100, 'localhost', {})

    def tearDown(self):
        self.shards_controller.drop_all()
        super(ShardsControllerTest, self).tearDown()

    def test_create_succeeds(self):
        self.shards_controller.create(str(uuid.uuid1()),
                                      100, 'localhost', {})

    def test_create_replaces_on_duplicate_insert(self):
        name = str(uuid.uuid1())
        self.shards_controller.create(name,
                                      100, 'localhost', {})
        self.shards_controller.create(name,
                                      111, 'localhost2', {})
        entry = self.shards_controller.get(name)
        self._shard_expects(entry, xname=name, xweight=111,
                            xlocation='localhost2')

    def _shard_expects(self, shard, xname, xweight, xlocation):
        self.assertIn('name', shard)
        self.assertEqual(shard['name'], xname)
        self.assertIn('weight', shard)
        self.assertEqual(shard['weight'], xweight)
        self.assertIn('uri', shard)
        self.assertEqual(shard['uri'], xlocation)

    def test_get_returns_expected_content(self):
        res = self.shards_controller.get(self.shard)
        self._shard_expects(res, self.shard, 100, 'localhost')
        self.assertNotIn('options', res)

    def test_detailed_get_returns_expected_content(self):
        res = self.shards_controller.get(self.shard, detailed=True)
        self.assertIn('options', res)
        self.assertEqual(res['options'], {})

    def test_get_raises_if_not_found(self):
        self.assertRaises(storage.errors.ShardDoesNotExist,
                          self.shards_controller.get, 'notexists')

    def test_exists(self):
        self.assertTrue(self.shards_controller.exists(self.shard))
        self.assertFalse(self.shards_controller.exists('notexists'))

    def test_update_raises_assertion_error_on_bad_fields(self):
        self.assertRaises(AssertionError, self.shards_controller.update,
                          self.shard)

    def test_update_works(self):
        self.shards_controller.update(self.shard, weight=101,
                                      uri='redis://localhost',
                                      options={'a': 1})
        res = self.shards_controller.get(self.shard, detailed=True)
        self._shard_expects(res, self.shard, 101, 'redis://localhost')
        self.assertEqual(res['options'], {'a': 1})

    def test_delete_works(self):
        self.shards_controller.delete(self.shard)
        self.assertFalse(self.shards_controller.exists(self.shard))

    def test_delete_nonexistent_is_silent(self):
        self.shards_controller.delete('nonexisting')

    def test_drop_all_leads_to_empty_listing(self):
        self.shards_controller.drop_all()
        cursor = self.shards_controller.list()
        self.assertRaises(StopIteration, next, cursor)

    def test_listing_simple(self):
        # NOTE(cpp-cabrera): base entry interferes with listing results
        self.shards_controller.delete(self.shard)

        for i in range(15):
            self.shards_controller.create(str(i), i, str(i), {})

        res = list(self.shards_controller.list())
        self.assertEqual(len(res), 10)
        for i, entry in enumerate(res):
            self._shard_expects(entry, str(i), i, str(i))
            self.assertNotIn('options', entry)

        res = list(self.shards_controller.list(limit=5))
        self.assertEqual(len(res), 5)

        res = next(self.shards_controller.list(marker='3'))
        self._shard_expects(res, '4', 4, '4')

        res = list(self.shards_controller.list(detailed=True))
        self.assertEqual(len(res), 10)
        for i, entry in enumerate(res):
            self._shard_expects(entry, str(i), i, str(i))
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
        self.assertIn('shard', entry)
        self.assertIsInstance(entry['queue'], six.text_type)
        self.assertIsInstance(entry['project'], six.text_type)
        self.assertIsInstance(entry['shard'], six.text_type)

    def _check_value(self, entry, xqueue, xproject, xshard):
        self.assertEqual(entry['queue'], xqueue)
        self.assertEqual(entry['project'], xproject)
        self.assertEqual(entry['shard'], xshard)

    def test_catalogue_entry_life_cycle(self):
        queue = self.queue
        project = self.project

        # check listing is initially empty
        for p in self.controller.list(project):
            self.fail('There should be no entries at this time')

        # create a listing, check its length
        with helpers.shard_entries(self.controller, 10) as expect:
            project = expect[0][0]
            xs = list(self.controller.list(project))
            self.assertEqual(len(xs), 10)

        # create, check existence, delete
        with helpers.shard_entry(self.controller, project, queue, u'a'):
            self.assertTrue(self.controller.exists(project, queue))

        # verify it no longer exists
        self.assertFalse(self.controller.exists(project, queue))

        # verify it isn't listable
        self.assertEqual(len(list(self.controller.list(project))), 0)

    def test_list(self):
        with helpers.shard_entries(self.controller, 10) as expect:
            values = zip(self.controller.list(u'_'), expect)
            for e, x in values:
                p, q, s = x
                self._check_structure(e)
                self._check_value(e, xqueue=q, xproject=p, xshard=s)

    def test_update(self):
        with helpers.shard_entry(self.controller, self.project,
                                 self.queue, u'a') as expect:
            p, q, s = expect
            self.controller.update(p, q, shard=u'b')
            entry = self.controller.get(p, q)
            self._check_value(entry, xqueue=q, xproject=p, xshard=u'b')

    def test_update_raises_when_entry_does_not_exist(self):
        self.assertRaises(errors.QueueNotMapped,
                          self.controller.update,
                          'not', 'not', 'a')

    def test_get(self):
        with helpers.shard_entry(self.controller,
                                 self.project,
                                 self.queue, u'a') as expect:
            p, q, s = expect
            e = self.controller.get(p, q)
            self._check_value(e, xqueue=q, xproject=p, xshard=s)

    def test_get_raises_if_does_not_exist(self):
        with helpers.shard_entry(self.controller,
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
        with helpers.shard_entry(self.controller,
                                 self.project,
                                 self.queue, u'a') as expect:
            p, q, _ = expect
            self.assertTrue(self.controller.exists(p, q))
        self.assertFalse(self.controller.exists('nada', 'not_here'))


def _insert_fixtures(controller, queue_name, project=None,
                     client_uuid=None, num=4, ttl=120):

    def messages():
        for n in xrange(num):
            yield {
                'ttl': ttl,
                'body': {
                    'event': 'Event number {0}'.format(n)
                }}

    controller.post(queue_name, messages(),
                    project=project, client_uuid=client_uuid)

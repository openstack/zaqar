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

from marconi import storage
from marconi.storage import exceptions
from marconi.tests import util as testing


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
            self.skipTest('%s is not an instance of %s. Tests not supported' %
                          (self.controller_class, self.controller_base_class))

        self.driver = self.driver_class()
        self.controller = self.controller_class(self.driver)


class QueueControllerTest(ControllerBaseTest):
    """Queue Controller base tests."""
    controller_base_class = storage.QueueBase

    def setUp(self):
        super(QueueControllerTest, self).setUp()
        self.message_controller = self.driver.message_controller
        self.claim_controller = self.driver.claim_controller

    def test_list(self):
        num = 15
        for queue in xrange(num):
            self.controller.upsert(queue, {}, project=self.project)

        interaction = self.controller.list(project=self.project,
                                           detailed=True)
        queues = list(interaction.next())

        self.assertEquals(all(map(lambda queue:
                                  'name' in queue and
                                  'metadata' in queue, queues)), True)
        self.assertEquals(len(queues), 10)

        interaction = self.controller.list(project=self.project,
                                           marker=interaction.next())
        queues = list(interaction.next())

        self.assertEquals(all(map(lambda queue:
                                  'name' in queue and
                                  'metadata' not in queue, queues)), True)
        self.assertEquals(len(queues), 5)

    def test_queue_lifecycle(self):
        # Test Queue Creation
        created = self.controller.upsert('test', project=self.project,
                                         metadata=dict(topic='test_queue'))

        self.assertTrue(created)

        # Test Queue retrieval
        queue = self.controller.get('test', project=self.project)
        self.assertIsNotNone(queue)

        # Test Queue Update
        created = self.controller.upsert('test', project=self.project,
                                         metadata=dict(meta='test_meta'))
        self.assertFalse(created)

        queue = self.controller.get('test', project=self.project)
        self.assertEqual(queue['meta'], 'test_meta')

        # Test Queue Statistic
        _insert_fixtures(self.message_controller, 'test',
                         project=self.project, client_uuid='my_uuid', num=12)

        countof = self.controller.stats('test', project=self.project)
        self.assertEqual(countof['messages']['free'], 12)

        # Test Queue Deletion
        self.controller.delete('test', project=self.project)

        # Test DoesNotExist Exception
        self.assertRaises(storage.exceptions.DoesNotExist,
                          self.controller.get, 'test',
                          project=self.project)


class MessageControllerTest(ControllerBaseTest):
    """Message Controller base tests.

    NOTE(flaper87): Implementations of this class should
    override the tearDown method in order
    to clean up storage's state.
    """
    queue_name = 'test_queue'
    controller_base_class = storage.MessageBase

    def setUp(self):
        super(MessageControllerTest, self).setUp()

        # Lets create a queue
        self.queue_controller = self.driver.queue_controller
        self.claim_controller = self.driver.claim_controller
        self.queue_controller.upsert(self.queue_name, {},
                                     project=self.project)

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
                                            client_uuid='unused'))
        self.assertEqual(len(created), 1)

        # Test Message Get
        self.controller.get(queue_name, created[0], project=self.project)

        # Test Message Deletion
        self.controller.delete(queue_name, created[0], project=self.project)

        # Test does not exist
        messages = self.controller.get(queue_name, message_ids=created,
                                       project=self.project)
        self.assertRaises(StopIteration, messages.next)

    def test_get_multi(self):
        _insert_fixtures(self.controller, self.queue_name,
                         project=self.project, client_uuid='my_uuid', num=15)

        def load_messages(expected, *args, **kwargs):
            interaction = self.controller.list(*args, **kwargs)
            msgs = list(interaction.next())
            self.assertEqual(len(msgs), expected)
            return interaction

        # Test all messages, echo False and uuid
        load_messages(0, self.queue_name, project=self.project,
                      client_uuid='my_uuid')

        # Test all messages and limit
        load_messages(15, self.queue_name, project=self.project, limit=20,
                      echo=True)

        # Test all messages, echo True, and uuid
        interaction = load_messages(10, self.queue_name, echo=True,
                                    project=self.project,
                                    client_uuid='my_uuid')

        # Test all messages, echo True, uuid and marker
        load_messages(5, self.queue_name, echo=True, project=self.project,
                      marker=interaction.next(), client_uuid='my_uuid')

    def test_get_multi_by_id(self):
        messages_in = [{'ttl': 120, 'body': 0}, {'ttl': 240, 'body': 1}]
        ids = self.controller.post(self.queue_name, messages_in,
                                   project=self.project,
                                   client_uuid='my_uuid')

        messages_out = self.controller.get(self.queue_name, ids,
                                           project=self.project)

        for idx, message in enumerate(messages_out):
            self.assertEquals(message['body'], idx)

    def test_claim_effects(self):
        _insert_fixtures(self.controller, self.queue_name,
                         project=self.project, client_uuid='my_uuid', num=12)

        meta = {'ttl': 70, 'grace': 60}

        another_cid, _ = self.claim_controller.create(self.queue_name, meta,
                                                      project=self.project)
        cid, msgs = self.claim_controller.create(self.queue_name, meta,
                                                 project=self.project)
        [msg1, msg2] = msgs

        # A wrong claim does not ensure the message deletion
        with testing.expect(storage.exceptions.NotPermitted):
            self.controller.delete(self.queue_name, msg1['id'],
                                   project=self.project,
                                   claim=another_cid)

        # Make sure a message can be deleted with a claim
        self.controller.delete(self.queue_name, msg1['id'],
                               project=self.project,
                               claim=cid)

        with testing.expect(StopIteration):
            self.controller.get(self.queue_name, msg1['id'],
                                project=self.project).next()

        # Make sure such a deletion is idempotent
        self.controller.delete(self.queue_name, msg1['id'],
                               project=self.project,
                               claim=cid)

        # A non-existing claim does not ensure the message deletion
        self.claim_controller.delete(self.queue_name, cid,
                                     project=self.project)

        with testing.expect(storage.exceptions.NotPermitted):
            self.controller.delete(self.queue_name, msg2['id'],
                                   project=self.project,
                                   claim=cid)

    def test_expired_message(self):
        messages = [{'body': 3.14, 'ttl': 0}]

        [msgid] = self.controller.post(self.queue_name, messages,
                                       project=self.project,
                                       client_uuid='my_uuid')

        with testing.expect(StopIteration):
            self.controller.get(self.queue_name, msgid,
                                project=self.project).next()

        countof = self.queue_controller.stats(self.queue_name,
                                              project=self.project)
        self.assertEquals(countof['messages']['free'], 0)

    def test_bad_id(self):
        # A malformed ID should result in an error. This
        # doesn't hurt anything, since an attacker could just
        # read the source code anyway to find out how IDs are
        # implemented. Plus, if someone is just trying to
        # get a message that they don't own, they would
        # more likely just list the messages, not try to
        # guess an ID of an arbitrary message.

        queue = 'foo'
        project = '480924'
        self.queue_controller.upsert(queue, {}, project)

        bad_message_id = 'xyz'
        with testing.expect(exceptions.MalformedID):
            self.controller.delete(queue, bad_message_id, project)

        with testing.expect(exceptions.MalformedID):
            self.controller.get(queue, bad_message_id, project).next()

    def test_bad_claim_id(self):
        self.queue_controller.upsert('unused', {}, '480924')
        [msgid] = self.controller.post('unused',
                                       [{'body': {}, 'ttl': 10}],
                                       project='480924',
                                       client_uuid='unused')

        bad_claim_id = '; DROP TABLE queues'
        with testing.expect(exceptions.MalformedID):
            self.controller.delete('unused', msgid,
                                   project='480924',
                                   claim=bad_claim_id)

    def test_bad_marker(self):
        queue = 'foo'
        project = '480924'
        self.queue_controller.upsert(queue, {}, project)

        bad_marker = 'xyz'
        func = self.controller.list
        results = func(queue, project, marker=bad_marker)
        self.assertRaises(exceptions.MalformedMarker, results.next)


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
        self.queue_controller.upsert(self.queue_name, {},
                                     project=self.project)

    def tearDown(self):
        self.queue_controller.delete(self.queue_name, project=self.project)
        super(ClaimControllerTest, self).tearDown()

    def test_claim_lifecycle(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid='my_uuid', num=20)

        meta = {'ttl': 70, 'grace': 30}

        # Make sure create works
        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project,
                                                    limit=15)

        messages = list(messages)
        self.assertEquals(len(messages), 15)

        # Ensure Queue stats
        countof = self.queue_controller.stats(self.queue_name,
                                              project=self.project)
        self.assertEqual(countof['messages']['claimed'], 15)
        self.assertEqual(countof['messages']['free'], 5)

        # Make sure get works
        claim, messages2 = self.controller.get(self.queue_name, claim_id,
                                               project=self.project)

        messages2 = list(messages2)
        self.assertEquals(len(messages2), 15)
        self.assertEquals(messages, messages2)
        self.assertEquals(claim['ttl'], 70)
        self.assertEquals(claim['id'], claim_id)

        new_meta = {'ttl': 100, 'grace': 60}
        self.controller.update(self.queue_name, claim_id,
                               new_meta, project=self.project)

        # Make sure update works
        claim, messages2 = self.controller.get(self.queue_name, claim_id,
                                               project=self.project)

        messages2 = list(messages2)
        self.assertEquals(len(messages2), 15)

        # TODO(zyuan): Add some tests to ensure the ttl is
        # extended/not-extended.
        for msg1, msg2 in zip(messages, messages2):
            self.assertEquals(msg1['body'], msg2['body'])

        self.assertEquals(claim['ttl'], 100)
        self.assertEquals(claim['id'], claim_id)

        # Make sure delete works
        self.controller.delete(self.queue_name, claim_id,
                               project=self.project)

        self.assertRaises(storage.exceptions.ClaimDoesNotExist,
                          self.controller.get, self.queue_name,
                          claim_id, project=self.project)

    def test_extend_lifetime(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid='my_uuid',
                         num=20, ttl=120)

        meta = {'ttl': 777, 'grace': 0}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEquals(message['ttl'], 777)

    def test_extend_lifetime_with_grace_1(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid='my_uuid',
                         num=20, ttl=120)

        meta = {'ttl': 777, 'grace': 23}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEquals(message['ttl'], 800)

    def test_extend_lifetime_with_grace_2(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid='my_uuid',
                         num=20, ttl=120)

        # Although ttl is less than the message's TTL, the grace
        # period puts it just over the edge.
        meta = {'ttl': 100, 'grace': 22}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEquals(message['ttl'], 122)

    def test_do_not_extend_lifetime(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         project=self.project, client_uuid='my_uuid',
                         num=20, ttl=120)

        # Choose a ttl that is less than the message's current TTL
        meta = {'ttl': 60, 'grace': 30}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        for message in messages:
            self.assertEquals(message['ttl'], 120)

    def test_expired_claim(self):
        meta = {'ttl': 0, 'grace': 60}

        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    project=self.project)

        with testing.expect(storage.exceptions.DoesNotExist):
            self.controller.get(self.queue_name, claim_id,
                                project=self.project)

        with testing.expect(storage.exceptions.DoesNotExist):
            self.controller.update(self.queue_name, claim_id,
                                   meta, project=self.project)

    def test_illformed_id(self):
        # any ill-formed IDs should be regarded as non-existing ones.

        self.queue_controller.upsert('unused', {}, '480924')
        self.controller.delete('unused', 'illformed', '480924')

        with testing.expect(exceptions.DoesNotExist):
            self.controller.update('unused', 'illformed',
                                   {'ttl': 40}, '480924')


def _insert_fixtures(controller, queue_name, project=None,
                     client_uuid=None, num=4, ttl=120):

    def messages():
        for n in xrange(num):
            yield {
                'ttl': ttl,
                'body': {
                    'event': 'Event number %s' % n
                }}
    controller.post(queue_name, messages(),
                    project=project, client_uuid=client_uuid)

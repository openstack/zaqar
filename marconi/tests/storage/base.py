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
from marconi.tests import util as testing


class ControllerBaseTest(testing.TestBase):
    tenant = "tenant"
    driver_class = None
    controller_class = None
    controller_base_class = None

    def setUp(self):
        super(ControllerBaseTest, self).setUp()

        if not self.driver_class:
            self.skipTest("No driver class specified")

        if not issubclass(self.controller_class, self.controller_base_class):
            self.skipTest("%s is not an instance of %s. Tests not supported" %
                          (self.controller_class, self.controller_base_class))

        self.driver = self.driver_class()
        self.controller = self.controller_class(self.driver)


class QueueControllerTest(ControllerBaseTest):
    """
    Queue Controller base tests
    """
    controller_base_class = storage.QueueBase

    def setUp(self):
        super(QueueControllerTest, self).setUp()
        self.message_controller = self.driver.message_controller
        self.claim_controller = self.driver.claim_controller

    def test_list(self):
        num = 4
        for queue in xrange(num):
            self.controller.upsert(queue, {}, tenant=self.tenant)

        queues = self.controller.list(tenant=self.tenant)

        counter = 0
        for queue in queues:
            self.assertEqual(len(queue), 2)
            self.assertIn("name", queue)
            self.assertIn("metadata", queue)
            counter += 1
        self.assertEqual(counter, num)

    def test_queue_lifecycle(self):
        # Test Queue Creation
        created = self.controller.upsert("test", tenant=self.tenant,
                                         metadata=dict(topic="test_queue"))

        self.assertTrue(created)

        # Test Queue retrieval
        queue = self.controller.get("test", tenant=self.tenant)
        self.assertIsNotNone(queue)

        # Test Queue Update
        created = self.controller.upsert("test", tenant=self.tenant,
                                         metadata=dict(meta="test_meta"))
        self.assertFalse(created)

        queue = self.controller.get("test", tenant=self.tenant)
        self.assertEqual(queue["meta"], "test_meta")

        # Test Queue Statistic
        _insert_fixtures(self.message_controller, "test",
                         tenant=self.tenant, client_uuid="my_uuid", num=12)

        countof = self.controller.stats("test", tenant=self.tenant)
        self.assertEqual(countof['messages']['total'], 12)

        # Test Queue Deletion
        self.controller.delete("test", tenant=self.tenant)

        # Test DoesNotExist Exception
        self.assertRaises(storage.exceptions.DoesNotExist,
                          self.controller.get, "test",
                          tenant=self.tenant)


class MessageControllerTest(ControllerBaseTest):
    """
    Message Controller base tests

    NOTE(flaper87): Implementations of this class should
    override the tearDown method in order
    to clean up storage's state.
    """
    queue_name = "test_queue"
    controller_base_class = storage.MessageBase

    def setUp(self):
        super(MessageControllerTest, self).setUp()

        # Lets create a queue
        self.queue_controller = self.driver.queue_controller
        self.queue_controller.upsert(self.queue_name, {},
                                     tenant=self.tenant)

    def tearDown(self):
        self.queue_controller.delete(self.queue_name, tenant=self.tenant)
        super(MessageControllerTest, self).tearDown()

    def test_message_lifecycle(self):
        queue_name = self.queue_name

        messages = [
            {
                "ttl": 60,
                "body": {
                    "event": "BackupStarted",
                    "backupId": "c378813c-3f0b-11e2-ad92-7823d2b0f3ce"
                }
            },
        ]

        # Test Message Creation
        created = list(self.controller.post(queue_name, messages,
                                            tenant=self.tenant,
                                            client_uuid="unused"))
        self.assertEqual(len(created), 1)

        # Test Message Get
        self.controller.get(queue_name, created[0], tenant=self.tenant)

        # Test Message Deletion
        self.controller.delete(queue_name, created[0], tenant=self.tenant)

        # Test DoesNotExist
        self.assertRaises(storage.exceptions.DoesNotExist,
                          self.controller.get,
                          queue_name, message_id=created[0],
                          tenant=self.tenant)

    def test_qet_multi(self):
        _insert_fixtures(self.controller, self.queue_name,
                         tenant=self.tenant, client_uuid="my_uuid", num=20)

        def load_messages(expected, *args, **kwargs):
            msgs = list(self.controller.list(*args, **kwargs))
            self.assertEqual(len(msgs), expected)
            return msgs

        # Test all messages, echo False and no uuid
        load_messages(10, self.queue_name, tenant=self.tenant)

        # Test all messages, echo False and uuid
        load_messages(0, self.queue_name, tenant=self.tenant,
                      client_uuid="my_uuid")

        # Test all messages and limit
        load_messages(20, self.queue_name, tenant=self.tenant, limit=20)

        # Test all messages, echo True, and uuid
        msgs = load_messages(10, self.queue_name, echo=True,
                             tenant=self.tenant, client_uuid="my_uuid")

        # Test all messages, echo False, no uuid and marker
        msgs = load_messages(10, self.queue_name, tenant=self.tenant,
                             marker=msgs[4]["marker"])

        # Test all messages, echo True, uuid and marker
        load_messages(5, self.queue_name, echo=True, tenant=self.tenant,
                      marker=msgs[9]["marker"], client_uuid="my_uuid")


class ClaimControllerTest(ControllerBaseTest):
    """
    Claim Controller base tests

    NOTE(flaper87): Implementations of this class should
    override the tearDown method in order
    to clean up storage's state.
    """
    queue_name = "test_queue"
    controller_base_class = storage.ClaimBase

    def setUp(self):
        super(ClaimControllerTest, self).setUp()

        # Lets create a queue
        self.queue_controller = self.driver.queue_controller
        self.message_controller = self.driver.message_controller
        self.queue_controller.upsert(self.queue_name, {},
                                     tenant=self.tenant)

    def tearDown(self):
        self.queue_controller.delete(self.queue_name)
        super(ClaimControllerTest, self).tearDown()

    def test_claim_lifecycle(self):
        _insert_fixtures(self.message_controller, self.queue_name,
                         tenant=self.tenant, client_uuid="my_uuid", num=20)

        meta = {"ttl": 70}

        # Make sure create works
        claim_id, messages = self.controller.create(self.queue_name, meta,
                                                    tenant=self.tenant,
                                                    limit=15)

        messages = list(messages)
        self.assertEquals(len(messages), 15)

        # Make sure get works
        claim, messages2 = self.controller.get(self.queue_name, claim_id,
                                               tenant=self.tenant)

        messages2 = list(messages2)
        self.assertEquals(len(messages2), 15)
        self.assertEquals(messages, messages2)
        self.assertEquals(claim["ttl"], 70)
        self.assertEquals(claim["id"], claim_id)

        new_meta = {"ttl": 100}
        self.controller.update(self.queue_name, claim_id,
                               new_meta, tenant=self.tenant)

        # Make sure update works
        claim, messages2 = self.controller.get(self.queue_name, claim_id,
                                               tenant=self.tenant)

        messages2 = list(messages2)
        self.assertEquals(len(messages2), 15)
        self.assertEquals(messages, messages2)
        self.assertEquals(claim["ttl"], 100)
        self.assertEquals(claim["id"], claim_id)

        # Make sure delete works
        self.controller.delete(self.queue_name, claim_id,
                               tenant=self.tenant)

        self.assertRaises(storage.exceptions.ClaimDoesNotExist,
                          self.controller.get, self.queue_name,
                          claim_id, tenant=self.tenant)


def _insert_fixtures(controller, queue_name, tenant=None,
                     client_uuid=None, num=4):

    def messages():
        for n in xrange(num):
            yield {
                "ttl": 60,
                "body": {
                    "event": "Event number %s" % n
                }}
    controller.post(queue_name, messages(),
                    tenant=tenant, client_uuid=client_uuid)

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
from marconi.tests.util import suite


class ControllerBaseTest(suite.TestSuite):
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

    def test_queue_lifecycle(self):
        # Test Queue Creation
        self.controller.create("test", ttl=10,
                               topic="test_queue")

        # Test Queue retrieval
        queue = self.controller.get("test")
        self.assertEqual(queue["name"], "test")
        self.assertEqual(queue["ttl"], 10)

        # Test Queue Update
        self.controller.update("tests", name="test1")
        queue = self.controller.get("test1")
        self.assertEqual(queue["ttl"], 10)

        # Test Queue Deletion
        self.controller.delete("test1")

        # Test DoesNotExist Exception
        self.assertRaises(storage.exceptions.DoesNotExist,
                          self.controller.get, "test1")


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
        self.queue_controller = self.driver.queue_controller()
        self.queue_controller.create(self.queue_name)

    def tearDown(self):
        self.queue_controller.delete(self.queue_name)
        super(MessageControllerTest, self).tearDown()

    def test_message_lifecycle(self):
        queue_name = self.queue_name

        messages = [
            {
                "body": {
                    "event": "BackupStarted",
                    "backupId": "c378813c-3f0b-11e2-ad92-7823d2b0f3ce"
                }
            },
        ]

        # Test Message Creation
        created = self.controller.post(queue_name, messages)
        self.assertEqual(len(created), 1)

        # Test Message Get
        self.controller.get(queue_name, message_id=created[0])

        # Test Message Deletion
        self.controller.delete(queue_name, created[0])

        # Test DoesNotExist
        self.assertRaises(storage.exceptions.DoesNotExist,
                          self.controller.get,
                          queue_name, created[0])

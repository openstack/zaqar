# Copyright (c) 2013 Rackspace, Inc.
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

from marconi.queues import storage
from marconi.queues.storage import sqlite
from marconi.queues.storage.sqlite import controllers
from marconi.tests.queues.storage import base


class SQliteQueueTests(base.QueueControllerTest):
    driver_class = sqlite.DataDriver
    controller_class = controllers.QueueController


class SQliteMessageTests(base.MessageControllerTest):
    driver_class = sqlite.DataDriver
    controller_class = controllers.MessageController

    def test_empty_queue_exception(self):
        queue_name = 'empty-queue-test'
        self.queue_controller.create(queue_name, None)

        self.assertRaises(storage.errors.QueueIsEmpty,
                          self.controller.first,
                          queue_name, None, sort=1)

    def test_invalid_sort_option(self):
        self.assertRaises(ValueError,
                          self.controller.first,
                          'foo', None, sort='dosomething()')


class SQliteClaimTests(base.ClaimControllerTest):
    driver_class = sqlite.DataDriver
    controller_class = controllers.ClaimController

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

from marconi.storage import exceptions
from marconi.storage import sqlite
from marconi.storage.sqlite import controllers
from marconi.tests.storage import base
from marconi.tests import util as testing


class SQliteQueueTests(base.QueueControllerTest):
    driver_class = sqlite.Driver
    controller_class = controllers.Queue


class SQliteMessageTests(base.MessageControllerTest):
    driver_class = sqlite.Driver
    controller_class = controllers.Message

    def setUp(self):
        super(SQliteMessageTests, self).setUp()
        self.queue_controller.upsert('unused', {}, '480924')

    def tearDown(self):
        self.queue_controller.delete('unused', '480924')
        super(SQliteMessageTests, self).tearDown()

    def test_illformed_id(self):
        # any ill-formed IDs should be regarded as non-existing ones.

        self.controller.delete('unused', 'illformed', '480924')

        msgs = list(self.controller.list('unused', '480924',
                                         marker='illformed'))

        self.assertEquals(len(msgs), 0)

        with testing.expected(exceptions.DoesNotExist):
            self.controller.get('unused', 'illformed', '480924')


class SQliteClaimTests(base.ClaimControllerTest):
    driver_class = sqlite.Driver
    controller_class = controllers.Claim

    def setUp(self):
        super(SQliteClaimTests, self).setUp()
        self.queue_controller.upsert('unused', {}, '480924')

    def tearDown(self):
        self.queue_controller.delete('unused', '480924')
        super(SQliteClaimTests, self).tearDown()

    def test_illformed_id(self):
        # any ill-formed IDs should be regarded as non-existing ones.

        self.controller.delete('unused', 'illformed', '480924')

        with testing.expected(exceptions.DoesNotExist):
            self.controller.update('unused', 'illformed',
                                   {'ttl': 40}, '480924')

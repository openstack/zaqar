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

import uuid

import mock

from zaqar.notification import notifier
from zaqar.notification import task
from zaqar import tests as testing


class NotifierTest(testing.TestBase):

    def setUp(self):
        super(NotifierTest, self).setUp()
        self.subscription = [{'subscriber': 'http://trigger.me'},
                             {'subscriber': 'http://call.me'},
                             {'subscriber': 'http://ping.me'}
                             ]
        self.cliend_id = uuid.uuid4()
        self.project = uuid.uuid4()
        self.messages = [{"ttl": 300,
                          "body": {"event": "BackupStarted",
                                   "backup_id": "c378813c-3f0b-11e2-ad92"}
                          },
                         {"body": {"event": "BackupProgress",
                                   "current_bytes": "0",
                                   "total_bytes": "99614720"}
                          }
                         ]

        ctlr = mock.MagicMock()
        ctlr.list = mock.Mock(return_value=iter(self.subscription))
        self.driver = notifier.NotifierDriver(subscription_controller=ctlr)

    def test_post(self):
        with mock.patch('requests.post') as mock_post:
            self.driver.post('fake_queue', self.messages,
                             self.client_uuid, self.project)
            mock_post.assert_called_with(self.subscription[0]['subscriber'],
                                         self.messages[0])
            mock_post.assert_called_with(self.subscription[1]['subscriber'],
                                         self.messages[0])
            mock_post.assert_called_with(self.subscription[2]['subscriber'],
                                         self.messages[0])
            mock_post.assert_called_with(self.subscription[0]['subscriber'],
                                         self.messages[1])
            mock_post.assert_called_with(self.subscription[1]['subscriber'],
                                         self.messages[1])
            mock_post.assert_called_with(self.subscription[2]['subscriber'],
                                         self.messages[1])

    def test_genrate_task(self):
        subscriber = self.subscription_list[0]['subscriber']
        new_task = self.driver._generate_task(subscriber, self.messages)
        self.assertIsInstance(new_task, task.webhook.WebhookTask)

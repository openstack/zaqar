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

import json
import uuid

import mock

from zaqar.notification import notifier
from zaqar import tests as testing


class NotifierTest(testing.TestBase):

    def setUp(self):
        super(NotifierTest, self).setUp()
        self.client_id = uuid.uuid4()
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
        # NOTE(Eva-i): NotifiedDriver adds "queue_name" key to each
        # message (dictionary), so final notifications look like this
        self.notifications = [{"ttl": 300,
                               "body": {"event": "BackupStarted",
                                        "backup_id":
                                            "c378813c-3f0b-11e2-ad92"},
                               "queue_name": "fake_queue"
                               },
                              {"body": {"event": "BackupProgress",
                                        "current_bytes": "0",
                                        "total_bytes": "99614720"},
                               "queue_name": "fake_queue"
                               }
                              ]

    def test_webhook(self):
        subscription = [{'subscriber': 'http://trigger_me',
                         'source': 'fake_queue'},
                        {'subscriber': 'http://call_me',
                         'source': 'fake_queue'},
                        {'subscriber': 'http://ping_me',
                         'source': 'fake_queue'}]
        ctlr = mock.MagicMock()
        ctlr.list = mock.Mock(return_value=iter([subscription]))
        driver = notifier.NotifierDriver(subscription_controller=ctlr)
        headers = {'Content-Type': 'application/json'}
        with mock.patch('requests.post') as mock_post:
            driver.post('fake_queue', self.messages, self.client_id,
                        self.project)
            driver.executor.shutdown()
            # Let's deserialize "data" from JSON string to dict in each mock
            # call, so we can do dict comparisons. JSON string comparisons
            # often fail, because dict keys can be serialized in different
            # order inside the string.
            for call in mock_post.call_args_list:
                call[1]['data'] = json.loads(call[1]['data'])
            # These are not real calls. In real calls each "data" argument is
            # serialized by json.dumps. But we made a substitution before,
            # so it will work.
            mock_post.assert_has_calls([
                mock.call(subscription[0]['subscriber'],
                          data=self.notifications[0],
                          headers=headers),
                mock.call(subscription[1]['subscriber'],
                          data=self.notifications[0],
                          headers=headers),
                mock.call(subscription[2]['subscriber'],
                          data=self.notifications[0],
                          headers=headers),
                mock.call(subscription[0]['subscriber'],
                          data=self.notifications[1],
                          headers=headers),
                mock.call(subscription[1]['subscriber'],
                          data=self.notifications[1],
                          headers=headers),
                mock.call(subscription[2]['subscriber'],
                          data=self.notifications[1],
                          headers=headers),
                ], any_order=True)
            self.assertEqual(6, len(mock_post.mock_calls))

    @mock.patch('subprocess.Popen')
    def test_mailto(self, mock_popen):
        subscription = [{'subscriber': 'mailto:aaa@example.com',
                         'source': 'fake_queue',
                        'options': {'subject': 'Hello',
                                    'from': 'zaqar@example.com'}},
                        {'subscriber': 'mailto:bbb@example.com',
                         'source': 'fake_queue',
                        'options': {'subject': 'Hello',
                                    'from': 'zaqar@example.com'}}]
        ctlr = mock.MagicMock()
        ctlr.list = mock.Mock(return_value=iter([subscription]))
        driver = notifier.NotifierDriver(subscription_controller=ctlr)
        called = set()
        msg = ('Content-Type: text/plain; charset="us-ascii"\n'
               'MIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\nto:'
               ' %(to)s\nfrom: %(from)s\nsubject: %(subject)s\n\n%(body)s')
        mail1 = msg % {'to': subscription[0]['subscriber'][7:],
                       'from': 'zaqar@example.com', 'subject': 'Hello',
                       'body': json.dumps(self.notifications[0])}
        mail2 = msg % {'to': subscription[0]['subscriber'][7:],
                       'from': 'zaqar@example.com', 'subject': 'Hello',
                       'body': json.dumps(self.notifications[1])}
        mail3 = msg % {'to': subscription[1]['subscriber'][7:],
                       'from': 'zaqar@example.com', 'subject': 'Hello',
                       'body': json.dumps(self.notifications[0])}
        mail4 = msg % {'to': subscription[1]['subscriber'][7:],
                       'from': 'zaqar@example.com', 'subject': 'Hello',
                       'body': json.dumps(self.notifications[1])}

        def _communicate(msg):
            called.add(msg)

        mock_process = mock.Mock()
        attrs = {'communicate': _communicate}
        mock_process.configure_mock(**attrs)
        mock_popen.return_value = mock_process
        driver.post('fake_queue', self.messages, self.client_id, self.project)
        driver.executor.shutdown()

        self.assertEqual(4, len(called))
        # Let's deserialize "body" from JSON string to dict and then serialize
        # it back to JSON, but sorted, allowing us make comparisons.
        mails = {mail1, mail2, mail3, mail4}
        mail_options = []
        mail_bodies = []
        for mail in mails:
            options, body = mail.split('\n\n')
            mail_options.append(options)
            mail_bodies.append(json.dumps(json.loads(body), sort_keys=True))
        called_options = []
        called_bodies = []
        for call in called:
            options, body = call.split('\n\n')
            called_options.append(options)
            called_bodies.append(json.dumps(json.loads(body), sort_keys=True))
        self.assertEqual(sorted(mail_options), sorted(called_options))
        self.assertEqual(sorted(mail_bodies), sorted(called_bodies))

    def test_post_no_subscriber(self):
        ctlr = mock.MagicMock()
        ctlr.list = mock.Mock(return_value=iter([[]]))
        driver = notifier.NotifierDriver(subscription_controller=ctlr)
        with mock.patch('requests.post') as mock_post:
            driver.post('fake_queue', self.messages, self.client_id,
                        self.project)
            driver.executor.shutdown()
            self.assertEqual(0, mock_post.call_count)

    def test_proper_notification_data(self):
        subscription = [{'subscriber': 'http://trigger_me',
                         'source': 'fake_queue'}]
        ctlr = mock.MagicMock()
        ctlr.list = mock.Mock(return_value=iter([subscription]))
        driver = notifier.NotifierDriver(subscription_controller=ctlr)
        with mock.patch('requests.post') as mock_post:
            driver.post('fake_queue', self.messages, self.client_id,
                        self.project)
            driver.executor.shutdown()
            self.assertEqual(2, mock_post.call_count)
            self.assertEqual(self.notifications[1],
                             json.loads(mock_post.call_args[1]['data']))

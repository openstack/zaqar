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

import ddt
import mock

from zaqar.common import urls
from zaqar.notification import notifier
from zaqar import tests as testing


@ddt.ddt
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
                               "queue_name": "fake_queue",
                               "Message_Type": "Notification"
                               },
                              {"body": {"event": "BackupProgress",
                                        "current_bytes": "0",
                                        "total_bytes": "99614720"},
                               "queue_name": "fake_queue",
                               "Message_Type": "Notification"
                               }
                              ]
        self.api_version = 'v2'

    def test_webhook(self):
        subscription = [{'subscriber': 'http://trigger_me',
                         'source': 'fake_queue',
                         'options': {}},
                        {'subscriber': 'http://call_me',
                         'source': 'fake_queue',
                         'options': {}},
                        {'subscriber': 'http://ping_me',
                         'source': 'fake_queue',
                         'options': {}}]
        ctlr = mock.MagicMock()
        ctlr.list = mock.Mock(return_value=iter([subscription, {}]))
        queue_ctlr = mock.MagicMock()
        queue_ctlr.get = mock.Mock(return_value={})
        driver = notifier.NotifierDriver(subscription_controller=ctlr,
                                         queue_controller=queue_ctlr)
        headers = {'Content-Type': 'application/json'}
        with mock.patch('requests.post') as mock_post:
            mock_post.return_value = None
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

    def test_webhook_post_data(self):
        post_data = {'foo': 'bar', 'egg': '$zaqar_message$'}
        subscription = [{'subscriber': 'http://trigger_me',
                         'source': 'fake_queue',
                         'options': {'post_data': json.dumps(post_data)}}]
        ctlr = mock.MagicMock()
        ctlr.list = mock.Mock(return_value=iter([subscription, {}]))
        queue_ctlr = mock.MagicMock()
        queue_ctlr.get = mock.Mock(return_value={})
        driver = notifier.NotifierDriver(subscription_controller=ctlr,
                                         queue_controller=queue_ctlr)
        headers = {'Content-Type': 'application/json'}
        with mock.patch('requests.post') as mock_post:
            mock_post.return_value = None
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
                          data={'foo': 'bar', 'egg': self.notifications[0]},
                          headers=headers),
                mock.call(subscription[0]['subscriber'],
                          data={'foo': 'bar', 'egg': self.notifications[1]},
                          headers=headers),
                ], any_order=True)
            self.assertEqual(2, len(mock_post.mock_calls))

    def test_marker(self):
        subscription1 = [{'subscriber': 'http://trigger_me1',
                          'source': 'fake_queue',
                          'options': {}}]
        subscription2 = [{'subscriber': 'http://trigger_me2',
                          'source': 'fake_queue',
                          'options': {}}]
        ctlr = mock.MagicMock()

        def mock_list(queue, project, marker):
            if not marker:
                return iter([subscription1, 'marker_id'])
            else:
                return iter([subscription2, {}])

        ctlr.list = mock_list
        queue_ctlr = mock.MagicMock()
        queue_ctlr.get = mock.Mock(return_value={})
        driver = notifier.NotifierDriver(subscription_controller=ctlr,
                                         queue_controller=queue_ctlr)
        headers = {'Content-Type': 'application/json'}
        with mock.patch('requests.post') as mock_post:
            mock_post.return_value = None
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
                mock.call(subscription1[0]['subscriber'],
                          data=self.notifications[0],
                          headers=headers),
                mock.call(subscription2[0]['subscriber'],
                          data=self.notifications[0],
                          headers=headers),
                ], any_order=True)
            self.assertEqual(4, len(mock_post.mock_calls))

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
        ctlr.list = mock.Mock(return_value=iter([subscription, {}]))
        queue_ctlr = mock.MagicMock()
        queue_ctlr.get = mock.Mock(return_value={})
        driver = notifier.NotifierDriver(subscription_controller=ctlr,
                                         queue_controller=queue_ctlr)
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
        ctlr.list = mock.Mock(return_value=iter([[], {}]))
        queue_ctlr = mock.MagicMock()
        queue_ctlr.get = mock.Mock(return_value={})
        driver = notifier.NotifierDriver(subscription_controller=ctlr,
                                         queue_controller=queue_ctlr)
        with mock.patch('requests.post') as mock_post:
            driver.post('fake_queue', self.messages, self.client_id,
                        self.project)
            driver.executor.shutdown()
            self.assertEqual(0, mock_post.call_count)

    def test_proper_notification_data(self):
        subscription = [{'subscriber': 'http://trigger_me',
                         'source': 'fake_queue',
                         'options': {}}]
        ctlr = mock.MagicMock()
        ctlr.list = mock.Mock(return_value=iter([subscription, {}]))
        queue_ctlr = mock.MagicMock()
        queue_ctlr.get = mock.Mock(return_value={})
        driver = notifier.NotifierDriver(subscription_controller=ctlr,
                                         queue_controller=queue_ctlr)
        with mock.patch('requests.post') as mock_post:
            mock_post.return_value = None
            driver.post('fake_queue', self.messages, self.client_id,
                        self.project)
            driver.executor.shutdown()
            self.assertEqual(2, mock_post.call_count)
            self.assertEqual(self.notifications[1],
                             json.loads(mock_post.call_args[1]['data']))

    @mock.patch('requests.post')
    def test_send_confirm_notification(self, mock_request):
        self.conf.notification.require_confirmation = True
        subscription = {'id': '5760c9fb3990b42e8b7c20bd',
                        'subscriber': 'http://trigger_me',
                        'source': 'fake_queue',
                        'options': {}}
        ctlr = mock.MagicMock()
        ctlr.list = mock.Mock(return_value=subscription)
        driver = notifier.NotifierDriver(subscription_controller=ctlr,
                                         require_confirmation=True)
        self.conf.signed_url.secret_key = 'test_key'
        driver.send_confirm_notification('test_queue', subscription, self.conf,
                                         str(self.project),
                                         api_version=self.api_version)
        driver.executor.shutdown()

        self.assertEqual(1, mock_request.call_count)
        expect_args = ['SubscribeBody', 'queue_name', 'URL-Methods',
                       'X-Project-ID', 'URL-Signature', 'URL-Paths', 'Message',
                       'URL-Expires', 'Message_Type', 'WSGISubscribeURL',
                       'WebSocketSubscribeURL' 'UnsubscribeBody']
        actual_args = json.loads(mock_request.call_args[1]['data']).keys()
        self.assertEqual(expect_args.sort(),
                         list(actual_args).sort())

    @mock.patch('requests.post')
    def test_send_confirm_notification_without_signed_url(self, mock_request):
        subscription = [{'subscriber': 'http://trigger_me',
                         'source': 'fake_queue', 'options': {}}]
        ctlr = mock.MagicMock()
        ctlr.list = mock.Mock(return_value=iter([subscription, {}]))
        driver = notifier.NotifierDriver(subscription_controller=ctlr)

        driver.send_confirm_notification('test_queue', subscription, self.conf,
                                         str(self.project), self.api_version)
        driver.executor.shutdown()

        self.assertEqual(0, mock_request.call_count)

    @mock.patch.object(urls, 'create_signed_url')
    def test_require_confirmation_false(self, mock_create_signed_url):
        subscription = [{'subscriber': 'http://trigger_me',
                         'source': 'fake_queue', 'options': {}}]
        ctlr = mock.MagicMock()
        driver = notifier.NotifierDriver(subscription_controller=ctlr,
                                         require_confirmation=False)

        driver.send_confirm_notification('test_queue', subscription, self.conf,
                                         str(self.project), self.api_version)

        self.assertFalse(mock_create_signed_url.called)

    def _make_confirm_string(self, conf, message, queue_name):
        confirmation_url = conf.notification.external_confirmation_url
        param_string_signature = '?Signature=' + message.get('signature')
        param_string_methods = '&Methods=' + message.get('methods')[0]
        param_string_paths = '&Paths=' + message.get('paths')[0]
        param_string_project = '&Project=' + message.get('project')
        param_string_expires = '&Expires=' + message.get('expires')
        param_string_confirm_url = '&Url=' + message.get('WSGISubscribeURL',
                                                         '')
        param_string_queue = '&Queue=' + queue_name
        confirm_url_string = (confirmation_url + param_string_signature +
                              param_string_methods + param_string_paths +
                              param_string_project + param_string_expires +
                              param_string_confirm_url + param_string_queue)
        return confirm_url_string

    @mock.patch('zaqar.common.urls.create_signed_url')
    @mock.patch('subprocess.Popen')
    def _send_confirm_notification_with_email(self, mock_popen,
                                              mock_signed_url,
                                              is_unsubscribed=False):
        subscription = {'id': '5760c9fb3990b42e8b7c20bd',
                        'subscriber': 'mailto:aaa@example.com',
                        'source': 'test_queue',
                        'options': {'subject': 'Hello',
                                    'from': 'zaqar@example.com'}
                        }
        driver = notifier.NotifierDriver(require_confirmation=True)
        self.conf.signed_url.secret_key = 'test_key'
        self.conf.notification.external_confirmation_url = 'http://127.0.0.1'
        self.conf.notification.require_confirmation = True

        message = {'methods': ['PUT'],
                   'paths': ['/v2/queues/test_queue/subscriptions/'
                             '5760c9fb3990b42e8b7c20bd/confirm'],
                   'project': str(self.project),
                   'expires': '2016-12-20T02:01:23',
                   'signature': 'e268676368c235dbe16e0e9ac40f2829a92c948288df'
                                '36e1cbabd9de73f698df',
                   }
        confirm_url = self._make_confirm_string(self.conf, message,
                                                'test_queue')
        msg = ('Content-Type: text/plain; charset="us-ascii"\n'
               'MIME-Version: 1.0\nContent-Transfer-Encoding: 7bit\nto:'
               ' %(to)s\nfrom: %(from)s\nsubject: %(subject)s\n\n%(body)s')
        if is_unsubscribed:
            e = self.conf.notification.unsubscribe_confirmation_email_template
            body = e['body']
            topic = e['topic']
            sender = e['sender']
        else:
            e = self.conf.notification.subscription_confirmation_email_template
            body = e['body']
            topic = e['topic']
            sender = e['sender']
        body = body.format(subscription['source'], str(self.project),
                           confirm_url)
        mail1 = msg % {'to': subscription['subscriber'][7:],
                       'from': sender,
                       'subject': topic,
                       'body': body}

        called = set()

        def _communicate(msg):
            called.add(msg)

        mock_process = mock.Mock()
        attrs = {'communicate': _communicate}
        mock_process.configure_mock(**attrs)
        mock_popen.return_value = mock_process
        mock_signed_url.return_value = message
        driver.send_confirm_notification('test_queue', subscription, self.conf,
                                         str(self.project),
                                         api_version=self.api_version,
                                         is_unsubscribed=is_unsubscribed)
        driver.executor.shutdown()

        self.assertEqual(1, mock_popen.call_count)
        options, body = mail1.split('\n\n')
        expec_options = [options]
        expect_body = [body]
        called_options = []
        called_bodies = []
        for call in called:
            options, body = call.split('\n\n')
            called_options.append(options)
            called_bodies.append(body)
        self.assertEqual(expec_options, called_options)
        self.assertEqual(expect_body, called_bodies)

    @ddt.data(False, True)
    def test_send_confirm_notification_with_email(self, is_unsub):
        self._send_confirm_notification_with_email(is_unsubscribed=is_unsub)

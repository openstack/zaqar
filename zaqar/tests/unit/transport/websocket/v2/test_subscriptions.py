# Copyright (c) 2015 Red Hat, Inc.
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
import time

import mock
import msgpack

from oslo_utils import uuidutils
from zaqar.common import auth
from zaqar.common import consts
from zaqar.storage import errors as storage_errors
from zaqar.tests.unit.transport.websocket import base
from zaqar.tests.unit.transport.websocket import utils as test_utils
from zaqar.transport.websocket import factory


class SubscriptionTest(base.V1_1Base):

    config_file = 'websocket_mongodb_subscriptions.conf'

    def setUp(self):
        super(SubscriptionTest, self).setUp()
        self.protocol = self.transport.factory()

        self.project_id = '7e55e1a7e'
        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': self.project_id
        }

        body = {'queue_name': 'kitkat'}
        req = test_utils.create_request(consts.QUEUE_CREATE,
                                        body, self.headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(resp['headers']['status'], 201)

        with mock.patch.object(self.protocol, 'sendMessage') as msg_mock:
            msg_mock.side_effect = validator
            self.protocol.onMessage(req, False)

    def tearDown(self):
        super(SubscriptionTest, self).tearDown()
        body = {'queue_name': 'kitkat'}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(consts.QUEUE_DELETE,
                                        body, self.headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(resp['headers']['status'], 204)

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

    def test_subscription_create(self):
        action = consts.SUBSCRIPTION_CREATE
        body = {'queue_name': 'kitkat', 'ttl': 600}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        subscription_factory = factory.NotificationFactory(None)
        subscription_factory.set_subscription_url('http://localhost:1234/')
        self.protocol._handler.set_subscription_factory(subscription_factory)

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        added_age = 1
        time.sleep(added_age)
        [subscriber] = list(
            next(
                self.boot.storage.subscription_controller.list(
                    'kitkat', self.project_id)))
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat',
            subscriber['id'], project=self.project_id)
        self.assertEqual('kitkat', subscriber['source'])
        self.assertEqual(600, subscriber['ttl'])
        self.assertEqual('http://localhost:1234/%s' % self.protocol.proto_id,
                         subscriber['subscriber'])
        self.assertLessEqual(added_age, subscriber['age'])

        response = {
            'body': {'message': 'Subscription kitkat created.',
                     'subscription_id': subscriber['id']},
            'headers': {'status': 201},
            'request': {'action': consts.SUBSCRIPTION_CREATE,
                        'body': {'queue_name': 'kitkat', 'ttl': 600},
                        'api': 'v2', 'headers': self.headers}}

        self.assertEqual(1, sender.call_count)
        self.assertEqual(response, json.loads(sender.call_args[0][0]))

        # Trigger protocol close
        self.protocol.onClose(True, 100, None)
        subscribers = list(
            next(
                self.boot.storage.subscription_controller.list(
                    'kitkat', self.project_id)))
        self.assertEqual([], subscribers)

    @mock.patch.object(auth, 'create_trust_id')
    def test_subscription_create_trust(self, create_trust):
        create_trust.return_value = 'trust_id'
        action = consts.SUBSCRIPTION_CREATE
        body = {'queue_name': 'kitkat', 'ttl': 600,
                'subscriber': 'trust+http://example.com'}
        self.protocol._auth_env = {}
        self.protocol._auth_env['X-USER-ID'] = 'user-id'
        self.protocol._auth_env['X-ROLES'] = 'my-roles'

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        send_mock.start()

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        [subscriber] = list(
            next(
                self.boot.storage.subscription_controller.list(
                    'kitkat', self.project_id)))
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat',
            subscriber['id'], project=self.project_id)
        self.assertEqual('trust+http://example.com',
                         subscriber['subscriber'])
        self.assertEqual({'trust_id': 'trust_id'}, subscriber['options'])

        self.assertEqual('user-id', create_trust.call_args[0][1])
        self.assertEqual(self.project_id, create_trust.call_args[0][2])
        self.assertEqual(['my-roles'], create_trust.call_args[0][3])

    def test_subscription_delete(self):
        sub = self.boot.storage.subscription_controller.create(
            'kitkat', '', 600, {}, project=self.project_id)
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat', sub,
            project=self.project_id)
        action = consts.SUBSCRIPTION_DELETE
        body = {'queue_name': 'kitkat', 'subscription_id': str(sub)}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        data = list(
            next(
                self.boot.storage.subscription_controller.list(
                    'kitkat', self.project_id)))
        self.assertEqual([], data)

        response = {
            'body': 'Subscription %s removed.' % str(sub),
            'headers': {'status': 204},
            'request': {'action': consts.SUBSCRIPTION_DELETE,
                        'body': {'queue_name': 'kitkat',
                                 'subscription_id': str(sub)},
                        'api': 'v2', 'headers': self.headers}}
        self.assertEqual(1, sender.call_count)
        self.assertEqual(response, json.loads(sender.call_args[0][0]))

    def test_subscription_create_no_queue(self):
        action = consts.SUBSCRIPTION_CREATE
        body = {'queue_name': 'shuffle', 'ttl': 600}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        subscription_factory = factory.NotificationFactory(None)
        subscription_factory.set_subscription_url('http://localhost:1234/')
        self.protocol._handler.set_subscription_factory(subscription_factory)

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        [subscriber] = list(
            next(
                self.boot.storage.subscription_controller.list(
                    'shuffle', self.project_id)))
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'shuffle',
            subscriber['id'], project=self.project_id)

        response = {
            'body': {'message': 'Subscription shuffle created.',
                     'subscription_id': subscriber['id']},
            'headers': {'status': 201},
            'request': {'action': consts.SUBSCRIPTION_CREATE,
                        'body': {'queue_name': 'shuffle', 'ttl': 600},
                        'api': 'v2', 'headers': self.headers}}

        self.assertEqual(1, sender.call_count)
        self.assertEqual(response, json.loads(sender.call_args[0][0]))

    def test_subscription_get(self):
        sub = self.boot.storage.subscription_controller.create(
            'kitkat', '', 600, {}, project=self.project_id)
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat', sub,
            project=self.project_id)
        action = consts.SUBSCRIPTION_GET
        body = {'queue_name': 'kitkat', 'subscription_id': str(sub)}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        expected_response_without_age = {
            'body': {'subscriber': '',
                     'source': 'kitkat',
                     'options': {},
                     'id': str(sub),
                     'ttl': 600,
                     'confirmed': False},
            'headers': {'status': 200},
            'request': {'action': consts.SUBSCRIPTION_GET,
                        'body': {'queue_name': 'kitkat',
                                 'subscription_id': str(sub)},
                        'api': 'v2', 'headers': self.headers}}

        self.assertEqual(1, sender.call_count)
        response = json.loads(sender.call_args[0][0])
        # Get and remove age from the actual response.
        actual_sub_age = response['body'].pop('age')
        self.assertLessEqual(0, actual_sub_age)
        self.assertEqual(expected_response_without_age, response)

    def test_subscription_list(self):
        sub = self.boot.storage.subscription_controller.create(
            'kitkat', '', 600, {}, project=self.project_id)
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat', sub,
            project=self.project_id)
        action = consts.SUBSCRIPTION_LIST
        body = {'queue_name': 'kitkat'}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        expected_response_without_age = {
            'body': {
                'subscriptions': [{
                    'subscriber': '',
                    'source': 'kitkat',
                    'options': {},
                    'id': str(sub),
                    'ttl': 600,
                    'confirmed': False}]},
            'headers': {'status': 200},
            'request': {'action': consts.SUBSCRIPTION_LIST,
                        'body': {'queue_name': 'kitkat'},
                        'api': 'v2', 'headers': self.headers}}
        self.assertEqual(1, sender.call_count)
        response = json.loads(sender.call_args[0][0])
        # Get and remove age from the actual response.
        actual_sub_age = response['body']['subscriptions'][0].pop('age')
        self.assertLessEqual(0, actual_sub_age)
        self.assertEqual(expected_response_without_age, response)

    def test_subscription_sustainable_notifications_format(self):
        # NOTE(Eva-i): The websocket subscription's notifications must be
        # sent in the same format, binary or text, as the format of the
        # subscription creation request.
        # This test checks that notifications keep their encoding format, even
        # if the client suddenly starts sending requests in another format.

        # Create a subscription in binary format
        action = consts.SUBSCRIPTION_CREATE
        body = {'queue_name': 'kitkat', 'ttl': 600}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        subscription_factory = factory.NotificationFactory(
            self.transport.factory)
        subscription_factory.set_subscription_url('http://localhost:1234/')
        self.protocol._handler.set_subscription_factory(subscription_factory)

        req = test_utils.create_binary_request(action, body, self.headers)
        self.protocol.onMessage(req, True)
        self.assertTrue(self.protocol.notify_in_binary)

        [subscriber] = list(
            next(
                self.boot.storage.subscription_controller.list(
                    'kitkat', self.project_id)))
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat',
            subscriber['id'], project=self.project_id)

        # Send a message in text format
        webhook_notification_send_mock = mock.patch('requests.post')
        self.addCleanup(webhook_notification_send_mock.stop)
        webhook_notification_sender = webhook_notification_send_mock.start()

        action = consts.MESSAGE_POST
        body = {"queue_name": "kitkat",
                "messages": [{'body': {'status': 'disco queen'}, 'ttl': 60}]}
        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)
        self.assertTrue(self.protocol.notify_in_binary)

        # Check that the server responded in text format to the message
        # creation request
        message_create_response = json.loads(sender.call_args_list[1][0][0])
        self.assertEqual(201, message_create_response['headers']['status'])

        # Fetch webhook notification that was intended to arrive to
        # notification protocol's listen address. Make subscription factory
        # send it as websocket notification to the client
        wh_notification = webhook_notification_sender.call_args[1]['data']
        subscription_factory.send_data(wh_notification, self.protocol.proto_id)

        # Check that the server sent the websocket notification in binary
        # format
        self.assertEqual(3, sender.call_count)
        ws_notification = msgpack.unpackb(sender.call_args_list[2][0][0],
                                          encoding='utf-8')
        self.assertEqual({'body': {'status': 'disco queen'}, 'ttl': 60,
                          'queue_name': 'kitkat',
                          'Message_Type': u'Notification'}, ws_notification)

    def test_list_returns_503_on_nopoolfound_exception(self):
        sub = self.boot.storage.subscription_controller.create(
            'kitkat', '', 600, {}, project=self.project_id)
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat', sub,
            project=self.project_id)
        action = consts.SUBSCRIPTION_LIST
        body = {'queue_name': 'kitkat'}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, self.headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(503, resp['headers']['status'])

        sender.side_effect = validator

        subscription_controller = self.boot.storage.subscription_controller

        with mock.patch.object(subscription_controller, 'list') as \
                mock_subscription_list:

            def subscription_generator():
                raise storage_errors.NoPoolFound()

            # This generator tries to be like subscription controller list
            # generator in some ways.
            def fake_generator():
                yield subscription_generator()
                yield {}
            mock_subscription_list.return_value = fake_generator()
            self.protocol.onMessage(req, False)

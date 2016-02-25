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
import uuid

import mock

from zaqar.storage import errors as storage_errors
from zaqar.tests.unit.transport.websocket import base
from zaqar.tests.unit.transport.websocket import utils as test_utils
from zaqar.transport.websocket import factory


class SubscriptionTest(base.V1_1Base):

    config_file = 'websocket_mongodb.conf'

    def setUp(self):
        super(SubscriptionTest, self).setUp()
        self.protocol = self.transport.factory()

        self.project_id = '7e55e1a7e'
        self.headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': self.project_id
        }

        action = 'queue_create'
        body = {'queue_name': 'kitkat'}
        req = test_utils.create_request(action, body, self.headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(resp['headers']['status'], 201)

        with mock.patch.object(self.protocol, 'sendMessage') as msg_mock:
            msg_mock.side_effect = validator
            self.protocol.onMessage(req, False)

    def tearDown(self):
        super(SubscriptionTest, self).tearDown()
        action = 'queue_delete'
        body = {'queue_name': 'kitkat'}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        send_mock.start()

        req = test_utils.create_request(action, body, self.headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(resp['headers']['status'], 204)

        send_mock.side_effect = validator
        self.protocol.onMessage(req, False)

    def test_subscription_create(self):
        action = 'subscription_create'
        body = {'queue_name': 'kitkat', 'ttl': 600}

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
                    'kitkat', self.project_id)))
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat',
            subscriber['id'], project=self.project_id)
        self.assertEqual('kitkat', subscriber['source'])
        self.assertEqual(600, subscriber['ttl'])
        self.assertEqual('http://localhost:1234/%s' % self.protocol.proto_id,
                         subscriber['subscriber'])

        self.boot.storage.subscription_controller.delete(
            'kitkat', subscriber['id'], project=self.project_id)

        response = {
            'body': {'message': 'Subscription kitkat created.',
                     'subscription_id': subscriber['id']},
            'headers': {'status': 201},
            'request': {'action': 'subscription_create',
                        'body': {'queue_name': 'kitkat', 'ttl': 600},
                        'api': 'v2', 'headers': self.headers}}

        self.assertEqual(1, sender.call_count)
        self.assertEqual(response, json.loads(sender.call_args[0][0]))

    def test_subscription_delete(self):
        sub = self.boot.storage.subscription_controller.create(
            'kitkat', '', 600, {}, project=self.project_id)
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat', sub,
            project=self.project_id)
        action = 'subscription_delete'
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
            'request': {'action': 'subscription_delete',
                        'body': {'queue_name': 'kitkat',
                                 'subscription_id': str(sub)},
                        'api': 'v2', 'headers': self.headers}}
        self.assertEqual(1, sender.call_count)
        self.assertEqual(response, json.loads(sender.call_args[0][0]))

    def test_subscription_create_no_queue(self):
        action = 'subscription_create'
        body = {'queue_name': 'shuffle', 'ttl': 600}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        subscription_factory = factory.NotificationFactory(None)
        subscription_factory.set_subscription_url('http://localhost:1234/')
        self.protocol._handler.set_subscription_factory(subscription_factory)

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        self.assertEqual(1, sender.call_count)
        self.assertEqual(
            'Queue shuffle does not exist.',
            json.loads(sender.call_args[0][0])['body']['error'])

    def test_subscription_get(self):
        sub = self.boot.storage.subscription_controller.create(
            'kitkat', '', 600, {}, project=self.project_id)
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat', sub,
            project=self.project_id)
        action = 'subscription_get'
        body = {'queue_name': 'kitkat', 'subscription_id': str(sub)}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        response = {
            'body': {'subscriber': '',
                     'source': 'kitkat',
                     'options': {},
                     'id': str(sub),
                     'ttl': 600},
            'headers': {'status': 200},
            'request': {'action': 'subscription_get',
                        'body': {'queue_name': 'kitkat',
                                 'subscription_id': str(sub)},
                        'api': 'v2', 'headers': self.headers}}

        self.assertEqual(1, sender.call_count)
        self.assertEqual(response, json.loads(sender.call_args[0][0]))

    def test_subscription_list(self):
        sub = self.boot.storage.subscription_controller.create(
            'kitkat', '', 600, {}, project=self.project_id)
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat', sub,
            project=self.project_id)
        action = 'subscription_list'
        body = {'queue_name': 'kitkat'}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, self.headers)
        self.protocol.onMessage(req, False)

        response = {
            'body': {
                'subscriptions': [{
                    'subscriber': '',
                    'source': 'kitkat',
                    'options': {},
                    'id': str(sub),
                    'ttl': 600}]},
            'headers': {'status': 200},
            'request': {'action': 'subscription_list',
                        'body': {'queue_name': 'kitkat'},
                        'api': 'v2', 'headers': self.headers}}

        self.assertEqual(1, sender.call_count)
        self.assertEqual(response, json.loads(sender.call_args[0][0]))

    def test_list_returns_503_on_nopoolfound_exception(self):
        sub = self.boot.storage.subscription_controller.create(
            'kitkat', '', 600, {}, project=self.project_id)
        self.addCleanup(
            self.boot.storage.subscription_controller.delete, 'kitkat', sub,
            project=self.project_id)
        action = 'subscription_list'
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

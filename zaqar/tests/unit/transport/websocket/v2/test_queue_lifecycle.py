# Copyright (c) 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import json
import uuid

import ddt
import mock

from zaqar.storage import errors as storage_errors
from zaqar import tests as testing
from zaqar.tests.unit.transport.websocket import base
from zaqar.tests.unit.transport.websocket import utils as test_utils


@ddt.ddt
class QueueLifecycleBaseTest(base.V2Base):

    config_file = "websocket_mongodb.conf"

    def setUp(self):
        super(QueueLifecycleBaseTest, self).setUp()
        self.protocol = self.transport.factory()

    def test_empty_project_id(self):
        action = "queue_create"
        body = {"queue_name": "kitkat",
                "metadata": {
                    "key": {
                        "key2": "value",
                        "key3": [1, 2, 3, 4, 5]}
                    }
                }
        headers = {'Client-ID': str(uuid.uuid4())}
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(400, resp['headers']['status'])

        with mock.patch.object(self.protocol, 'sendMessage') as msg_mock:
            msg_mock.side_effect = validator
            self.protocol.onMessage(req, False)

    @ddt.data('480924', 'foo')
    def test_basics_thoroughly(self, project_id):
        # Stats are empty - queue not created yet
        action = "queue_get_stats"
        body = {"queue_name": "gummybears"}
        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': project_id
        }

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(404, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Create
        action = "queue_create"
        body = {"queue_name": "gummybears",
                "metadata": {
                    "key": {
                        "key2": "value",
                        "key3": [1, 2, 3, 4, 5]},
                    "messages": {"ttl": 600},
                    }
                }
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(201, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Fetch metadata
        action = "queue_get"
        body = {"queue_name": "gummybears"}
        meta = {"messages": {"ttl": 600},
                "key": {
                    "key2": "value",
                    "key3": [1, 2, 3, 4, 5]}
                }
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(200, resp['headers']['status'])
            self.assertEqual(meta, resp['body'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Stats empty queue
        action = "queue_get_stats"
        body = {"queue_name": "gummybears"}
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(200, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Delete
        action = "queue_delete"
        body = {"queue_name": "gummybears"}
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(204, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Get non-existent stats
        action = "queue_get_stats"
        body = {"queue_name": "gummybears"}
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(404, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

    def test_name_restrictions(self):
        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': 'test-project'
        }
        action = "queue_create"
        body = {"queue_name": 'marsbar',
                "metadata": {
                    "key": {
                        "key2": "value",
                        "key3": [1, 2, 3, 4, 5]},
                    "messages": {"ttl": 600},
                    }
                }

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(201, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        body["queue_name"] = "m@rsb@r"
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(400, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        body["queue_name"] = "marsbar" * 10
        req = test_utils.create_request(action, body, headers)
        self.protocol.onMessage(req, False)

    def test_project_id_restriction(self):
        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': 'test-project' * 30
        }
        action = "queue_create"
        body = {"queue_name": 'poptart'}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(400, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        headers['X-Project-ID'] = 'test-project'
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(201, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

    def test_non_ascii_name(self):
        test_params = ((u'/queues/non-ascii-n\u0153me', 'utf-8'),
                       (u'/queues/non-ascii-n\xc4me', 'iso8859-1'))

        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': 'test-project' * 30
        }
        action = "queue_create"
        body = {"queue_name": test_params[0]}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(400, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        body = {"queue_name": test_params[1]}
        req = test_utils.create_request(action, body, headers)

        self.protocol.onMessage(req, False)

    def test_no_metadata(self):
        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': 'test-project'
        }
        action = "queue_create"
        body = {"queue_name": "fizbat"}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(201, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(204, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

    @ddt.data('{', '[]', '.', '  ')
    def test_bad_metadata(self, meta):
        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': 'test-project' * 30
        }
        action = "queue_create"
        body = {"queue_name": "fizbat",
                "metadata": meta}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(400, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

    def test_too_much_metadata(self):
        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': 'test-project'
        }
        action = "queue_create"
        body = {"queue_name": "buttertoffee",
                "metadata": {"messages": {"ttl": 600},
                             "padding": "x"}
                }

        max_size = self.transport_cfg.max_queue_metadata
        body["metadata"]["padding"] = "x" * max_size

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(400, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

    def test_way_too_much_metadata(self):
        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': 'test-project'
        }
        action = "queue_create"
        body = {"queue_name": "peppermint",
                "metadata": {"messages": {"ttl": 600},
                             "padding": "x"}
                }

        max_size = self.transport_cfg.max_queue_metadata
        body["metadata"]["padding"] = "x" * max_size * 5

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(400, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

    def test_update_metadata(self):
        self.skip("Implement patch method")
        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': 'test-project'
        }
        action = "queue_create"
        body = {"queue_name": "bonobon"}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        # Create
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(201, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Set meta
        meta1 = {"messages": {"ttl": 600}, "padding": "x"}
        body["metadata"] = meta1

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(204, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Get
        action = "queue_get"
        body = {"queue_name": "bonobon"}

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(204, resp['headers']['status'])
            self.assertEqual(meta1, resp['body'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Update
        action = "queue_create"
        meta2 = {"messages": {"ttl": 100}, "padding": "y"}
        body["metadata"] = meta2

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(204, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Get again
        action = "queue_get"
        body = {"queue_name": "bonobon"}

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(200, resp['headers']['status'])
            self.assertEqual(meta2, resp['body'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

    def test_list(self):
        arbitrary_number = 644079696574693
        project_id = str(arbitrary_number)
        client_id = str(uuid.uuid4())
        headers = {
            'X-Project-ID': project_id,
            'Client-ID': client_id
        }

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        # NOTE(kgriffs): It's important that this one sort after the one
        # above. This is in order to prove that bug/1236605 is fixed, and
        # stays fixed!
        # NOTE(vkmc): In websockets as well!
        alt_project_id = str(arbitrary_number + 1)

        # List empty
        action = "queue_list"
        body = {}

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(200, resp['headers']['status'])
            self.assertEqual([], resp['body']['queues'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Payload exceeded
        body = {'limit': 21}
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(400, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # Create some
        def create_queue(project_id, queue_name, metadata):
            altheaders = {'Client-ID': client_id}
            if project_id is not None:
                altheaders['X-Project-ID'] = project_id
            action = 'queue_create'
            body['queue_name'] = queue_name
            body['metadata'] = metadata

            req = test_utils.create_request(action, body, altheaders)

            def validator(resp, isBinary):
                resp = json.loads(resp)
                self.assertEqual(201, resp['headers']['status'])

            sender.side_effect = validator
            self.protocol.onMessage(req, False)

        create_queue(project_id, 'q1', {"node": 31})
        create_queue(project_id, 'q2', {"node": 32})
        create_queue(project_id, 'q3', {"node": 33})

        create_queue(alt_project_id, 'q3', {"alt": 1})

        # List (limit)
        body = {'limit': 2}
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(2, len(resp['body']['queues']))

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # List (no metadata, get all)
        body = {'limit': 5}
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(200, resp['headers']['status'])
            # Ensure we didn't pick up the queue from the alt project.
            self.assertEqual(3, len(resp['body']['queues']))

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # List with metadata
        body = {'detailed': True}
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(200, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        action = "queue_get"
        body = {"queue_name": "q1"}
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(200, resp['headers']['status'])
            self.assertEqual({"node": 31}, resp['body'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # List tail
        action = "queue_list"
        body = {}
        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(200, resp['headers']['status'])

        sender.side_effect = validator
        self.protocol.onMessage(req, False)

        # List manually-constructed tail
        body = {'marker': "zzz"}
        req = test_utils.create_request(action, body, headers)
        self.protocol.onMessage(req, False)

    def test_list_returns_503_on_nopoolfound_exception(self):
        headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': 'test-project'
        }
        action = "queue_list"
        body = {}

        send_mock = mock.patch.object(self.protocol, 'sendMessage')
        self.addCleanup(send_mock.stop)
        sender = send_mock.start()

        req = test_utils.create_request(action, body, headers)

        def validator(resp, isBinary):
            resp = json.loads(resp)
            self.assertEqual(503, resp['headers']['status'])

        sender.side_effect = validator

        queue_controller = self.boot.storage.queue_controller

        with mock.patch.object(queue_controller, 'list') as mock_queue_list:

            def queue_generator():
                raise storage_errors.NoPoolFound()

            # This generator tries to be like queue controller list generator
            # in some ways.
            def fake_generator():
                yield queue_generator()
                yield {}
            mock_queue_list.return_value = fake_generator()
            self.protocol.onMessage(req, False)


class TestQueueLifecycleMongoDB(QueueLifecycleBaseTest):

    config_file = 'websocket_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestQueueLifecycleMongoDB, self).setUp()

    def tearDown(self):
        storage = self.boot.storage._storage
        connection = storage.connection

        connection.drop_database(self.boot.control.queues_database)

        for db in storage.message_databases:
            connection.drop_database(db)

        super(TestQueueLifecycleMongoDB, self).tearDown()

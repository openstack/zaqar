# Copyright (c) 2013 Rackspace, Inc.
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


import ddt
import falcon
import mock
from oslo_serialization import jsonutils
from oslo_utils import uuidutils
import six

from zaqar.storage import errors as storage_errors
from zaqar import tests as testing
from zaqar.tests.unit.transport.wsgi import base


@ddt.ddt
class TestQueueLifecycleMongoDB(base.V1_1Base):

    config_file = 'wsgi_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestQueueLifecycleMongoDB, self).setUp()

        self.queue_path = self.url_prefix + '/queues'
        self.gumshoe_queue_path = self.queue_path + '/gumshoe'
        self.fizbat_queue_path = self.queue_path + '/fizbat'

        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': '3387309841abc_'
        }

    def tearDown(self):
        storage = self.boot.storage._storage
        connection = storage.connection

        connection.drop_database(self.boot.control.queues_database)

        for db in storage.message_databases:
            connection.drop_database(db)

        super(TestQueueLifecycleMongoDB, self).tearDown()

    def test_empty_project_id(self):
        headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': ''
        }

        self.simulate_put(self.gumshoe_queue_path, headers=headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_delete(self.gumshoe_queue_path, headers=headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data('480924', 'foo')
    def test_basics_thoroughly(self, project_id):
        headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': project_id
        }
        gumshoe_queue_path_stats = self.gumshoe_queue_path + '/stats'

        # Stats are empty - queue not created yet
        self.simulate_get(gumshoe_queue_path_stats, headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Create
        doc = '{"messages": {"ttl": 600}}'
        self.simulate_put(self.gumshoe_queue_path,
                          headers=headers, body=doc)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        location = self.srmock.headers_dict['Location']
        self.assertEqual(self.gumshoe_queue_path, location)

        # Fetch metadata
        result = self.simulate_get(self.gumshoe_queue_path,
                                   headers=headers)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(jsonutils.loads(doc), result_doc)

        # Stats empty queue
        self.simulate_get(gumshoe_queue_path_stats, headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Delete
        self.simulate_delete(self.gumshoe_queue_path, headers=headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Get non-existent stats
        self.simulate_get(gumshoe_queue_path_stats, headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_name_restrictions(self):
        self.simulate_put(self.queue_path + '/Nice-Boat_2',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self.simulate_put(self.queue_path + '/Nice-Bo@t',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_put(self.queue_path + '/_' + 'niceboat' * 8,
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_project_id_restriction(self):
        muvluv_queue_path = self.queue_path + '/Muv-Luv'

        self.simulate_put(muvluv_queue_path,
                          headers={'Client-ID': uuidutils.generate_uuid(),
                                   'X-Project-ID': 'JAM Project' * 24})
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # no charset restrictions
        self.simulate_put(muvluv_queue_path,
                          headers={'Client-ID': uuidutils.generate_uuid(),
                                   'X-Project-ID': 'JAM Project'})
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_non_ascii_name(self):
        test_params = ((u'/queues/non-ascii-n\u0153me', 'utf-8'),
                       (u'/queues/non-ascii-n\xc4me', 'iso8859-1'))

        for uri, enc in test_params:
            uri = self.url_prefix + uri

            if six.PY2:
                uri = uri.encode(enc)

            self.simulate_put(uri, headers=self.headers)
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

            self.simulate_delete(uri, headers=self.headers)
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_no_metadata(self):
        self.simulate_put(self.fizbat_queue_path,
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self.simulate_put(self.fizbat_queue_path, body='',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    @ddt.data('{', '[]', '.', '  ')
    def test_bad_metadata(self, document):
        self.simulate_put(self.fizbat_queue_path,
                          headers=self.headers,
                          body=document)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_too_much_metadata(self):
        self.simulate_put(self.fizbat_queue_path, headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size - (len(doc) - 10) + 1

        doc = doc.format(pad='x' * padding_len)

        self.simulate_put(self.fizbat_queue_path,
                          headers=self.headers,
                          body=doc)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_way_too_much_metadata(self):
        self.simulate_put(self.fizbat_queue_path, headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size * 100

        doc = doc.format(pad='x' * padding_len)

        self.simulate_put(self.fizbat_queue_path,
                          headers=self.headers, body=doc)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_custom_metadata(self):
        # Set
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size - (len(doc) - 2)

        doc = doc.format(pad='x' * padding_len)
        self.simulate_put(self.fizbat_queue_path,
                          headers=self.headers,
                          body=doc)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # Get
        result = self.simulate_get(self.fizbat_queue_path,
                                   headers=self.headers)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(jsonutils.loads(doc), result_doc)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_update_metadata(self):
        self.skip("This should use patch instead")
        xyz_queue_path = self.url_prefix + '/queues/xyz'
        xyz_queue_path_metadata = xyz_queue_path

        # Create
        self.simulate_put(xyz_queue_path, headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # Set meta
        doc1 = '{"messages": {"ttl": 600}}'
        self.simulate_put(xyz_queue_path_metadata,
                          headers=self.headers,
                          body=doc1)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Update
        doc2 = '{"messages": {"ttl": 100}}'
        self.simulate_put(xyz_queue_path_metadata,
                          headers=self.headers,
                          body=doc2)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Get
        result = self.simulate_get(xyz_queue_path_metadata,
                                   headers=self.headers)
        result_doc = jsonutils.loads(result[0])

        self.assertEqual(jsonutils.loads(doc2), result_doc)

    def test_list(self):
        arbitrary_number = 644079696574693
        project_id = str(arbitrary_number)
        client_id = uuidutils.generate_uuid()
        header = {
            'X-Project-ID': project_id,
            'Client-ID': client_id
        }

        # NOTE(kgriffs): It's important that this one sort after the one
        # above. This is in order to prove that bug/1236605 is fixed, and
        # stays fixed!
        alt_project_id = str(arbitrary_number + 1)

        # List empty
        result = self.simulate_get(self.queue_path, headers=header)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        results = jsonutils.loads(result[0])
        self.assertEqual([], results['queues'])
        self.assertIn('links', results)
        self.assertEqual(0, len(results['links']))

        # Payload exceeded
        self.simulate_get(self.queue_path, headers=header,
                          query_string='limit=21')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Create some
        def create_queue(name, project_id, body):
            altheader = {'Client-ID': client_id}
            if project_id is not None:
                altheader['X-Project-ID'] = project_id
            uri = self.queue_path + '/' + name
            self.simulate_put(uri, headers=altheader, body=body)

        create_queue('q1', project_id, '{"node": 31}')
        create_queue('q2', project_id, '{"node": 32}')
        create_queue('q3', project_id, '{"node": 33}')

        create_queue('q3', alt_project_id, '{"alt": 1}')

        # List (limit)
        result = self.simulate_get(self.queue_path, headers=header,
                                   query_string='limit=2')

        result_doc = jsonutils.loads(result[0])
        self.assertEqual(2, len(result_doc['queues']))

        # List (no metadata, get all)
        result = self.simulate_get(self.queue_path,
                                   headers=header, query_string='limit=5')

        result_doc = jsonutils.loads(result[0])
        [target, params] = result_doc['links'][0]['href'].split('?')

        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Ensure we didn't pick up the queue from the alt project.
        queues = result_doc['queues']
        self.assertEqual(3, len(queues))

        # List with metadata
        result = self.simulate_get(self.queue_path, headers=header,
                                   query_string='detailed=true')

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        result_doc = jsonutils.loads(result[0])
        [target, params] = result_doc['links'][0]['href'].split('?')

        queue = result_doc['queues'][0]
        result = self.simulate_get(queue['href'], headers=header)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(queue['metadata'], result_doc)
        self.assertEqual({'node': 31}, result_doc)

        # List tail
        self.simulate_get(target, headers=header, query_string=params)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # List manually-constructed tail
        self.simulate_get(target, headers=header, query_string='marker=zzz')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_list_returns_503_on_nopoolfound_exception(self):
        arbitrary_number = 644079696574693
        project_id = str(arbitrary_number)
        client_id = uuidutils.generate_uuid()
        header = {
            'X-Project-ID': project_id,
            'Client-ID': client_id
        }

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
            self.simulate_get(self.queue_path, headers=header)
            self.assertEqual(falcon.HTTP_503, self.srmock.status)


class TestQueueLifecycleFaultyDriver(base.V1_1BaseFaulty):

    config_file = 'wsgi_faulty.conf'

    def test_simple(self):
        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': '338730984abc_1'
        }

        gumshoe_queue_path = self.url_prefix + '/queues/gumshoe'
        doc = '{"messages": {"ttl": 600}}'
        self.simulate_put(gumshoe_queue_path,
                          headers=self.headers,
                          body=doc)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        location = ('Location', gumshoe_queue_path)
        self.assertNotIn(location, self.srmock.headers)

        result = self.simulate_get(gumshoe_queue_path,
                                   headers=self.headers)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(falcon.HTTP_503, self.srmock.status)
        self.assertNotEqual(result_doc, jsonutils.loads(doc))

        self.simulate_get(gumshoe_queue_path + '/stats',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_get(self.url_prefix + '/queues',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_delete(gumshoe_queue_path, headers=self.headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

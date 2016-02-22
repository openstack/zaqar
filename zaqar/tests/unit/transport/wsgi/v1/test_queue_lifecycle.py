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
import six

from zaqar.storage import errors as storage_errors
from zaqar import tests as testing
from zaqar.tests.unit.transport.wsgi import base


@ddt.ddt
class TestQueueLifecycleMongoDB(base.V1Base):

    config_file = 'wsgi_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestQueueLifecycleMongoDB, self).setUp()

        self.queue_path = self.url_prefix + '/queues'
        self.gumshoe_queue_path = self.queue_path + '/gumshoe'
        self.fizbat_queue_path = self.queue_path + '/fizbat'
        self.fizbat_queue_path_metadata = self.fizbat_queue_path + '/metadata'

    def tearDown(self):
        storage = self.boot.storage._storage
        connection = storage.connection

        connection.drop_database(self.boot.control.queues_database)

        for db in storage.message_databases:
            connection.drop_database(db)

        super(TestQueueLifecycleMongoDB, self).tearDown()

    def test_empty_project_id(self):
        self.simulate_get(self.gumshoe_queue_path, '')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_put(self.gumshoe_queue_path, '')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_head(self.gumshoe_queue_path, '')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_delete(self.gumshoe_queue_path, '')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data('480924', 'foo', None)
    def test_basics_thoroughly(self, project_id):
        gumshoe_queue_path_metadata = self.gumshoe_queue_path + '/metadata'
        gumshoe_queue_path_stats = self.gumshoe_queue_path + '/stats'

        # Stats not found - queue not created yet
        self.simulate_get(gumshoe_queue_path_stats, project_id)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Metadata not found - queue not created yet
        self.simulate_get(gumshoe_queue_path_metadata, project_id)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Create
        self.simulate_put(self.gumshoe_queue_path, project_id)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        location = self.srmock.headers_dict['Location']
        self.assertEqual(self.gumshoe_queue_path, location)

        # Ensure queue existence
        self.simulate_head(self.gumshoe_queue_path, project_id)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Add metadata
        doc = '{"messages": {"ttl": 600}}'
        self.simulate_put(gumshoe_queue_path_metadata,
                          project_id, body=doc)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Fetch metadata
        result = self.simulate_get(gumshoe_queue_path_metadata,
                                   project_id)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(jsonutils.loads(doc), result_doc)

        # Stats empty queue
        self.simulate_get(gumshoe_queue_path_stats, project_id)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Delete
        self.simulate_delete(self.gumshoe_queue_path, project_id)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Get non-existent queue
        self.simulate_get(self.gumshoe_queue_path, project_id)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Get non-existent stats
        self.simulate_get(gumshoe_queue_path_stats, project_id)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # Get non-existent metadata
        self.simulate_get(gumshoe_queue_path_metadata, project_id)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_name_restrictions(self):
        self.simulate_put(self.queue_path + '/Nice-Boat_2')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self.simulate_put(self.queue_path + '/Nice-Bo@t')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_put(self.queue_path + '/_' + 'niceboat' * 8)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_project_id_restriction(self):
        muvluv_queue_path = self.queue_path + '/Muv-Luv'

        self.simulate_put(muvluv_queue_path,
                          headers={'X-Project-ID': 'JAM Project' * 24})
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # no charset restrictions
        self.simulate_put(muvluv_queue_path,
                          headers={'X-Project-ID': 'JAM Project'})
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_non_ascii_name(self):
        test_params = ((u'/queues/non-ascii-n\u0153me', 'utf-8'),
                       (u'/queues/non-ascii-n\xc4me', 'iso8859-1'))

        for uri, enc in test_params:
            uri = self.url_prefix + uri

            if six.PY2:
                uri = uri.encode(enc)

            self.simulate_put(uri)
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

            self.simulate_get(uri)
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

            self.simulate_delete(uri)
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_no_metadata(self):
        self.simulate_put(self.fizbat_queue_path)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self.simulate_put(self.fizbat_queue_path_metadata)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_put(self.fizbat_queue_path_metadata, body='')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data('{', '[]', '.', '  ', '')
    def test_bad_metadata(self, document):
        self.simulate_put(self.fizbat_queue_path, '7e55e1a7e')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self.simulate_put(self.fizbat_queue_path_metadata, '7e55e1a7e',
                          body=document)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_too_much_metadata(self):
        self.simulate_put(self.fizbat_queue_path, '7e55e1a7e')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size - (len(doc) - 10) + 1

        doc = doc.format(pad='x' * padding_len)

        self.simulate_put(self.fizbat_queue_path_metadata, '7e55e1a7e',
                          body=doc)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_way_too_much_metadata(self):
        self.simulate_put(self.fizbat_queue_path, '7e55e1a7e')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size * 100

        doc = doc.format(pad='x' * padding_len)

        self.simulate_put(self.fizbat_queue_path_metadata,
                          '7e55e1a7e', body=doc)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_custom_metadata(self):
        self.simulate_put(self.fizbat_queue_path, '480924')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # Set
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size - (len(doc) - 2)

        doc = doc.format(pad='x' * padding_len)
        self.simulate_put(self.fizbat_queue_path_metadata, '480924', body=doc)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Get
        result = self.simulate_get(self.fizbat_queue_path_metadata, '480924')
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(jsonutils.loads(doc), result_doc)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_update_metadata(self):
        xyz_queue_path = self.url_prefix + '/queues/xyz'
        xyz_queue_path_metadata = xyz_queue_path + '/metadata'

        # Create
        project_id = '480924'
        self.simulate_put(xyz_queue_path, project_id)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # Set meta
        doc1 = '{"messages": {"ttl": 600}}'
        self.simulate_put(xyz_queue_path_metadata, project_id, body=doc1)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Update
        doc2 = '{"messages": {"ttl": 100}}'
        self.simulate_put(xyz_queue_path_metadata, project_id, body=doc2)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Get
        result = self.simulate_get(xyz_queue_path_metadata, project_id)
        result_doc = jsonutils.loads(result[0])

        self.assertEqual(jsonutils.loads(doc2), result_doc)
        self.assertEqual(xyz_queue_path_metadata,
                         self.srmock.headers_dict['Content-Location'])

    def test_list(self):
        arbitrary_number = 644079696574693
        project_id = str(arbitrary_number)

        # NOTE(kgriffs): It's important that this one sort after the one
        # above. This is in order to prove that bug/1236605 is fixed, and
        # stays fixed!
        alt_project_id = str(arbitrary_number + 1)

        # List empty
        self.simulate_get(self.queue_path, project_id)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Payload exceeded
        self.simulate_get(self.queue_path, project_id, query_string='limit=21')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Create some
        def create_queue(name, project_id, body):
            uri = self.queue_path + '/' + name
            self.simulate_put(uri, project_id)
            self.simulate_put(uri + '/metadata', project_id, body=body)

        create_queue('g1', None, '{"answer": 42}')
        create_queue('g2', None, '{"answer": 42}')

        create_queue('q1', project_id, '{"node": 31}')
        create_queue('q2', project_id, '{"node": 32}')
        create_queue('q3', project_id, '{"node": 33}')

        create_queue('q3', alt_project_id, '{"alt": 1}')

        # List (global queues)
        result = self.simulate_get(self.queue_path, None,
                                   query_string='limit=2&detailed=true')

        result_doc = jsonutils.loads(result[0])
        queues = result_doc['queues']
        self.assertEqual(2, len(queues))

        for queue in queues:
            self.assertEqual({'answer': 42}, queue['metadata'])

        # List (limit)
        result = self.simulate_get(self.queue_path, project_id,
                                   query_string='limit=2')

        result_doc = jsonutils.loads(result[0])
        self.assertEqual(2, len(result_doc['queues']))

        # List (no metadata, get all)
        result = self.simulate_get(self.queue_path,
                                   project_id, query_string='limit=5')

        result_doc = jsonutils.loads(result[0])
        [target, params] = result_doc['links'][0]['href'].split('?')

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(self.queue_path + '?limit=5',
                         self.srmock.headers_dict['Content-Location'])

        # Ensure we didn't pick up the queue from the alt project.
        queues = result_doc['queues']
        self.assertEqual(3, len(queues))

        for queue in queues:
            self.simulate_get(queue['href'] + '/metadata', project_id)
            self.assertEqual(falcon.HTTP_200, self.srmock.status)

            self.simulate_get(queue['href'] + '/metadata', 'imnothere')
            self.assertEqual(falcon.HTTP_404, self.srmock.status)

            self.assertNotIn('metadata', queue)

        # List with metadata
        result = self.simulate_get(self.queue_path, project_id,
                                   query_string='detailed=true')

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        result_doc = jsonutils.loads(result[0])
        [target, params] = result_doc['links'][0]['href'].split('?')

        queue = result_doc['queues'][0]
        result = self.simulate_get(queue['href'] + '/metadata', project_id)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(queue['metadata'], result_doc)
        self.assertEqual({'node': 31}, result_doc)

        # List tail
        self.simulate_get(target, project_id, query_string=params)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # List manually-constructed tail
        self.simulate_get(target, project_id, query_string='marker=zzz')
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_list_returns_503_on_nopoolfound_exception(self):
        arbitrary_number = 644079696574693
        project_id = str(arbitrary_number)
        header = {
            'X-Project-ID': project_id,
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


class TestQueueLifecycleFaultyDriver(base.V1BaseFaulty):

    config_file = 'wsgi_faulty.conf'

    def test_simple(self):
        gumshoe_queue_path = self.url_prefix + '/queues/gumshoe'
        doc = '{"messages": {"ttl": 600}}'
        self.simulate_put(gumshoe_queue_path, '480924', body=doc)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        location = ('Location', gumshoe_queue_path)
        self.assertNotIn(location, self.srmock.headers)

        result = self.simulate_get(gumshoe_queue_path + '/metadata', '480924')
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(falcon.HTTP_503, self.srmock.status)
        self.assertNotEqual(result_doc, jsonutils.loads(doc))

        self.simulate_get(gumshoe_queue_path + '/stats', '480924')
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_get(self.url_prefix + '/queues', '480924')
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_delete(gumshoe_queue_path, '480924')
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import json

import ddt
import falcon
import six

from . import base  # noqa
from marconi import tests as testing


@ddt.ddt
class QueueLifecycleBaseTest(base.TestBase):

    config_file = None

    def setUp(self):
        super(QueueLifecycleBaseTest, self).setUp()

    def test_empty_project_id(self):
        path = self.url_prefix + '/queues/gumshoe'

        self.simulate_get(path, '')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_put(path, '')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_head(path, '')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_delete(path, '')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data('480924', 'foo', None)
    def test_basics_thoroughly(self, project_id):
        path = self.url_prefix + '/queues/gumshoe'

        # Stats not found - queue not created yet
        self.simulate_get(path + '/stats', project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

        # Metadata not found - queue not created yet
        self.simulate_get(path + '/metadata', project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

        # Create
        self.simulate_put(path, project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        location = self.srmock.headers_dict['Location']
        self.assertEqual(location, self.url_prefix + '/queues/gumshoe')

        # Ensure queue existence
        self.simulate_head(path, project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Add metadata
        doc = '{"messages": {"ttl": 600}}'
        self.simulate_put(path + '/metadata', project_id, body=doc)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Fetch metadata
        result = self.simulate_get(path + '/metadata', project_id)
        result_doc = json.loads(result[0])
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertEqual(result_doc, json.loads(doc))

        # Stats empty queue
        self.simulate_get(path + '/stats', project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        # Delete
        self.simulate_delete(path, project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Get non-existent queue
        self.simulate_get(path, project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

        # Get non-existent stats
        self.simulate_get(path + '/stats', project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

        # Get non-existent metadata
        self.simulate_get(path + '/metadata', project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_name_restrictions(self):
        self.simulate_put(self.url_prefix + '/queues/Nice-Boat_2')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        self.simulate_put(self.url_prefix + '/queues/Nice-Bo@t')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_put(self.url_prefix + '/queues/_' + 'niceboat' * 8)
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_project_id_restriction(self):
        self.simulate_put(self.url_prefix + '/queues/Muv-Luv',
                          headers={'X-Project-ID': 'JAM Project' * 24})
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        # no charset restrictions
        self.simulate_put(self.url_prefix + '/queues/Muv-Luv',
                          headers={'X-Project-ID': 'JAM Project'})
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def test_non_ascii_name(self):
        test_params = ((u'/queues/non-ascii-n\u0153me', 'utf-8'),
                       (u'/queues/non-ascii-n\xc4me', 'iso8859-1'))

        for uri, enc in test_params:
            uri = self.url_prefix + uri

            if six.PY2:
                uri = uri.encode(enc)

            self.simulate_put(uri)
            self.assertEqual(self.srmock.status, falcon.HTTP_400)

            self.simulate_get(uri)
            self.assertEqual(self.srmock.status, falcon.HTTP_400)

            self.simulate_delete(uri)
            self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_no_metadata(self):
        self.simulate_put(self.url_prefix + '/queues/fizbat')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        self.simulate_put(self.url_prefix + '/queues/fizbat/metadata')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_put(self.url_prefix + '/queues/fizbat/metadata', body='')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data('{', '[]', '.', '  ', '')
    def test_bad_metadata(self, document):
        self.simulate_put(self.url_prefix + '/queues/fizbat', '7e55e1a7e')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        self.simulate_put(self.url_prefix + '/queues/fizbat/metadata',
                          '7e55e1a7e', body=document)
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_too_much_metadata(self):
        self.simulate_put(self.url_prefix + '/queues/fizbat', '7e55e1a7e')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size - (len(doc) - 10) + 1

        doc = doc.format(pad='x' * padding_len)

        self.simulate_put(self.url_prefix + '/queues/fizbat/metadata',
                          '7e55e1a7e', body=doc)
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_way_too_much_metadata(self):
        self.simulate_put(self.url_prefix + '/queues/fizbat', '7e55e1a7e')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size * 100

        doc = doc.format(pad='x' * padding_len)

        self.simulate_put(self.url_prefix + '/queues/fizbat/metadata',
                          '7e55e1a7e', body=doc)
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_custom_metadata(self):
        self.simulate_put(self.url_prefix + '/queues/fizbat', '480924')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        # Set
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size - (len(doc) - 2)

        doc = doc.format(pad='x' * padding_len)
        self.simulate_put(self.url_prefix + '/queues/fizbat/metadata',
                          '480924', body=doc)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Get
        result = self.simulate_get(self.url_prefix + '/queues/fizbat/metadata',
                                   '480924')
        result_doc = json.loads(result[0])
        self.assertEqual(result_doc, json.loads(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

    def test_update_metadata(self):
        # Create
        path = self.url_prefix + '/queues/xyz'
        project_id = '480924'
        self.simulate_put(path, project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        # Set meta
        doc1 = '{"messages": {"ttl": 600}}'
        self.simulate_put(path + '/metadata', project_id, body=doc1)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Update
        doc2 = '{"messages": {"ttl": 100}}'
        self.simulate_put(path + '/metadata', project_id, body=doc2)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Get
        result = self.simulate_get(path + '/metadata', project_id)
        result_doc = json.loads(result[0])

        self.assertEqual(result_doc, json.loads(doc2))
        self.assertEqual(self.srmock.headers_dict['Content-Location'],
                         path + '/metadata')

    def test_list(self):
        arbitrary_number = 644079696574693
        project_id = str(arbitrary_number)

        # NOTE(kgriffs): It's important that this one sort after the one
        # above. This is in order to prove that bug/1236605 is fixed, and
        # stays fixed!
        alt_project_id = str(arbitrary_number + 1)

        # List empty
        self.simulate_get(self.url_prefix + '/queues', project_id)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # Payload exceeded
        self.simulate_get(self.url_prefix + '/queues', project_id,
                          query_string='limit=21')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        # Create some
        def create_queue(name, project_id, body):
            uri = self.url_prefix + '/queues/' + name
            self.simulate_put(uri, project_id)
            self.simulate_put(uri + '/metadata', project_id, body=body)

        create_queue('g1', None, '{"answer": 42}')
        create_queue('g2', None, '{"answer": 42}')

        create_queue('q1', project_id, '{"node": 31}')
        create_queue('q2', project_id, '{"node": 32}')
        create_queue('q3', project_id, '{"node": 33}')

        create_queue('q3', alt_project_id, '{"alt": 1}')

        # List (global queues)
        result = self.simulate_get(self.url_prefix + '/queues', None,
                                   query_string='limit=2&detailed=true')

        result_doc = json.loads(result[0])
        queues = result_doc['queues']
        self.assertEqual(len(queues), 2)

        for queue in queues:
            self.assertEqual(queue['metadata'], {'answer': 42})

        # List (limit)
        result = self.simulate_get(self.url_prefix + '/queues', project_id,
                                   query_string='limit=2')

        result_doc = json.loads(result[0])
        self.assertEqual(len(result_doc['queues']), 2)

        # List (no metadata, get all)
        result = self.simulate_get(self.url_prefix + '/queues', project_id,
                                   query_string='limit=5')

        result_doc = json.loads(result[0])
        [target, params] = result_doc['links'][0]['href'].split('?')

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertEqual(self.srmock.headers_dict['Content-Location'],
                         self.url_prefix + '/queues?limit=5')

        # Ensure we didn't pick up the queue from the alt project.
        queues = result_doc['queues']
        self.assertEqual(len(queues), 3)

        for queue in queues:
            self.simulate_get(queue['href'] + '/metadata', project_id)
            self.assertEqual(self.srmock.status, falcon.HTTP_200)

            self.simulate_get(queue['href'] + '/metadata', 'imnothere')
            self.assertEqual(self.srmock.status, falcon.HTTP_404)

            self.assertNotIn('metadata', queue)

        # List with metadata
        result = self.simulate_get(self.url_prefix + '/queues', project_id,
                                   query_string='detailed=true')

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        result_doc = json.loads(result[0])
        [target, params] = result_doc['links'][0]['href'].split('?')

        queue = result_doc['queues'][0]
        result = self.simulate_get(queue['href'] + '/metadata', project_id)
        result_doc = json.loads(result[0])
        self.assertEqual(result_doc, queue['metadata'])
        self.assertEqual(result_doc, {'node': 31})

        # List tail
        self.simulate_get(target, project_id, query_string=params)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        # List manually-constructed tail
        self.simulate_get(target, project_id, query_string='marker=zzz')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)


class TestQueueLifecycleMongoDB(QueueLifecycleBaseTest):

    config_file = 'wsgi_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestQueueLifecycleMongoDB, self).setUp()

    def tearDown(self):
        storage = self.boot.storage._storage
        connection = storage.connection

        connection.drop_database(storage.queues_database)

        for db in storage.message_databases:
            connection.drop_database(db)

        super(TestQueueLifecycleMongoDB, self).tearDown()


class TestQueueLifecycleSqlalchemy(QueueLifecycleBaseTest):

    config_file = 'wsgi_sqlalchemy.conf'


class TestQueueLifecycleFaultyDriver(base.TestBaseFaulty):

    config_file = 'wsgi_faulty.conf'

    def test_simple(self):
        path = self.url_prefix + '/queues/gumshoe'
        doc = '{"messages": {"ttl": 600}}'
        self.simulate_put(path, '480924', body=doc)
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

        location = ('Location', path)
        self.assertNotIn(location, self.srmock.headers)

        result = self.simulate_get(path + '/metadata', '480924')
        result_doc = json.loads(result[0])
        self.assertEqual(self.srmock.status, falcon.HTTP_503)
        self.assertNotEqual(result_doc, json.loads(doc))

        self.simulate_get(path + '/stats', '480924')
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

        self.simulate_get(self.url_prefix + '/queues', '480924')
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

        self.simulate_delete(path, '480924')
        self.assertEqual(self.srmock.status, falcon.HTTP_503)

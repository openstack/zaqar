# Copyright (c) 2019 Rackspace, Inc.
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


from unittest import mock

import ddt
import falcon
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from zaqar.storage import errors as storage_errors
from zaqar import tests as testing
from zaqar.tests.unit.transport.wsgi import base


@ddt.ddt
class TestTopicLifecycleMongoDB(base.V2Base):

    config_file = 'wsgi_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super().setUp()

        self.topic_path = self.url_prefix + '/topics'
        self.mars_topic_path = self.topic_path + '/mars'
        self.venus_topic_path = self.topic_path + '/venus'

        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': '3387309841abc_'
        }

    def tearDown(self):
        control = self.boot.control
        storage = self.boot.storage._storage
        connection = storage.connection

        connection.drop_database(control.topics_database)

        for db in storage.message_databases:
            connection.drop_database(db)

        super().tearDown()

    def test_without_project_id(self):
        headers = {
            'Client-ID': uuidutils.generate_uuid(),
        }

        self.simulate_put(self.mars_topic_path, headers=headers,
                          need_project_id=False)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_delete(self.mars_topic_path, headers=headers,
                             need_project_id=False)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_empty_project_id(self):
        headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': ''
        }

        self.simulate_put(self.mars_topic_path, headers=headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_delete(self.mars_topic_path, headers=headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data('480924', 'foo')
    def test_basics_thoroughly(self, project_id):
        headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': project_id
        }
        mars_topic_path_stats = self.mars_topic_path + '/stats'

        # Stats are empty - topic not created yet
        self.simulate_get(mars_topic_path_stats, headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Create
        doc = '{"messages": {"ttl": 600}}'
        self.simulate_put(self.mars_topic_path,
                          headers=headers, body=doc)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        location = self.srmock.headers_dict['Location']
        self.assertEqual(location, self.mars_topic_path)

        # Fetch metadata
        result = self.simulate_get(self.mars_topic_path,
                                   headers=headers)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        ref_doc = jsonutils.loads(doc)
        ref_doc['_default_message_ttl'] = 3600
        ref_doc['_max_messages_post_size'] = 262144
        ref_doc['_default_message_delay'] = 0
        self.assertEqual(ref_doc, result_doc)

        # Stats empty topic
        self.simulate_get(mars_topic_path_stats, headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Delete
        self.simulate_delete(self.mars_topic_path, headers=headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Get non-existent stats
        self.simulate_get(mars_topic_path_stats, headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    @ddt.data('1234567890', '11111111111111111111111111111111111')
    def test_basics_thoroughly_with_different_client_id(self, client_id):
        self.conf.set_override('client_id_uuid_safe', 'off', 'transport')
        headers = {
            'Client-ID': client_id,
            'X-Project-ID': '480924'
        }
        mars_topic_path_stats = self.mars_topic_path + '/stats'

        # Stats are empty - topic not created yet
        self.simulate_get(mars_topic_path_stats, headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Create
        doc = '{"messages": {"ttl": 600}}'
        self.simulate_put(self.mars_topic_path,
                          headers=headers, body=doc)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        location = self.srmock.headers_dict['Location']
        self.assertEqual(location, self.mars_topic_path)

        # Fetch metadata
        result = self.simulate_get(self.mars_topic_path,
                                   headers=headers)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        ref_doc = jsonutils.loads(doc)
        ref_doc['_default_message_ttl'] = 3600
        ref_doc['_max_messages_post_size'] = 262144
        ref_doc['_default_message_delay'] = 0
        self.assertEqual(ref_doc, result_doc)

        # Stats empty topic
        self.simulate_get(mars_topic_path_stats, headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Delete
        self.simulate_delete(self.mars_topic_path, headers=headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        # Get non-existent stats
        self.simulate_get(mars_topic_path_stats, headers=headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_name_restrictions(self):
        self.simulate_put(self.topic_path + '/Nice-Boat_2',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self.simulate_put(self.topic_path + '/Nice-Bo@t',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_put(self.topic_path + '/_' + 'niceboat' * 8,
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_put(self.topic_path + '/Service.test_topic',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_project_id_restriction(self):
        muvluv_topic_path = self.topic_path + '/Muv-Luv'

        self.simulate_put(muvluv_topic_path,
                          headers={'Client-ID': uuidutils.generate_uuid(),
                                   'X-Project-ID': 'JAM Project' * 24})
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # no charset restrictions
        self.simulate_put(muvluv_topic_path,
                          headers={'Client-ID': uuidutils.generate_uuid(),
                                   'X-Project-ID': 'JAM Project'})
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_non_ascii_name(self):
        test_params = (('/topics/non-ascii-n\u0153me', 'utf-8'),
                       ('/topics/non-ascii-n\xc4me', 'iso8859-1'))

        for uri, enc in test_params:
            uri = self.url_prefix + uri

            self.simulate_put(uri, headers=self.headers)
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

            self.simulate_delete(uri, headers=self.headers)
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_no_metadata(self):
        self.simulate_put(self.venus_topic_path,
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self.simulate_put(self.venus_topic_path, body='',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        result = self.simulate_get(self.venus_topic_path,
                                   headers=self.headers)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(256 * 1024,
                         result_doc.get('_max_messages_post_size'))
        self.assertEqual(3600,
                         result_doc.get('_default_message_ttl'))
        self.assertEqual(0,
                         result_doc.get('_default_message_delay'))

    @ddt.data('{', '[]', '.', '  ')
    def test_bad_metadata(self, document):
        self.simulate_put(self.venus_topic_path,
                          headers=self.headers,
                          body=document)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_too_much_metadata(self):
        self.simulate_put(self.venus_topic_path, headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size - (len(doc) - 10) + 1

        doc = doc.format(pad='x' * padding_len)

        self.simulate_put(self.venus_topic_path,
                          headers=self.headers,
                          body=doc)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_way_too_much_metadata(self):
        self.simulate_put(self.venus_topic_path, headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size * 100

        doc = doc.format(pad='x' * padding_len)

        self.simulate_put(self.venus_topic_path,
                          headers=self.headers, body=doc)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_custom_metadata(self):
        # Set
        doc = '{{"messages": {{"ttl": 600}}, "padding": "{pad}"}}'

        max_size = self.transport_cfg.max_queue_metadata
        padding_len = max_size - (len(doc) - 2)

        doc = doc.format(pad='x' * padding_len)
        self.simulate_put(self.venus_topic_path,
                          headers=self.headers,
                          body=doc)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # Get
        result = self.simulate_get(self.venus_topic_path,
                                   headers=self.headers)
        result_doc = jsonutils.loads(result[0])
        ref_doc = jsonutils.loads(doc)
        ref_doc['_default_message_ttl'] = 3600
        ref_doc['_max_messages_post_size'] = 262144
        ref_doc['_default_message_delay'] = 0
        self.assertEqual(ref_doc, result_doc)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

    def test_update_metadata(self):
        xyz_topic_path = self.url_prefix + '/topics/xyz'
        xyz_topic_path_metadata = xyz_topic_path
        headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': uuidutils.generate_uuid()
        }
        # Create
        self.simulate_put(xyz_topic_path, headers=headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        headers.update({'Content-Type':
                        "application/openstack-messaging-v2.0-json-patch"})
        # add metadata
        doc1 = ('[{"op":"add", "path": "/metadata/key1", "value": 1},'
                '{"op":"add", "path": "/metadata/key2", "value": 1}]')
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc1)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # remove reserved metadata, zaqar will do nothing and return 200,
        # because
        doc3 = '[{"op":"remove", "path": "/metadata/_default_message_ttl"}]'
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc3)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # replace metadata
        doc2 = '[{"op":"replace", "path": "/metadata/key1", "value": 2}]'
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc2)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # replace reserved metadata, zaqar will store the reserved metadata
        doc2 = ('[{"op":"replace", "path": "/metadata/_default_message_ttl",'
                '"value": 300}]')
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc2)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Get
        result = self.simulate_get(xyz_topic_path_metadata,
                                   headers=headers)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual({'key1': 2, 'key2': 1,
                          '_default_message_ttl': 300,
                          '_max_messages_post_size': 262144,
                          '_default_message_delay': 0}, result_doc)

        # remove metadata
        doc3 = '[{"op":"remove", "path": "/metadata/key1"}]'
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc3)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # remove reserved metadata
        doc3 = '[{"op":"remove", "path": "/metadata/_default_message_ttl"}]'
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc3)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Get
        result = self.simulate_get(xyz_topic_path_metadata,
                                   headers=headers)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual({'key2': 1, '_default_message_ttl': 3600,
                          '_max_messages_post_size': 262144,
                          '_default_message_delay': 0}, result_doc)

        # replace non-existent metadata
        doc4 = '[{"op":"replace", "path": "/metadata/key3", "value":2}]'
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc4)
        self.assertEqual(falcon.HTTP_409, self.srmock.status)

        # remove non-existent metadata
        doc5 = '[{"op":"remove", "path": "/metadata/key3"}]'
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc5)
        self.assertEqual(falcon.HTTP_409, self.srmock.status)

        self.simulate_delete(xyz_topic_path, headers=headers)

        # add metadata to non-existent topic
        doc1 = ('[{"op":"add", "path": "/metadata/key1", "value": 1},'
                '{"op":"add", "path": "/metadata/key2", "value": 1}]')
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc1)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # replace metadata in non-existent topic
        doc4 = '[{"op":"replace", "path": "/metadata/key3", "value":2}]'
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc4)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

        # remove metadata from non-existent topic
        doc5 = '[{"op":"remove", "path": "/metadata/key3"}]'
        self.simulate_patch(xyz_topic_path_metadata,
                            headers=headers,
                            body=doc5)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

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
        result = self.simulate_get(self.topic_path, headers=header)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        results = jsonutils.loads(result[0])
        self.assertEqual([], results['topics'])
        self.assertIn('links', results)
        self.assertEqual(0, len(results['links']))

        # Payload exceeded
        self.simulate_get(self.topic_path, headers=header,
                          query_string='limit=21')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        # Create some
        def create_topic(name, project_id, body):
            altheader = {'Client-ID': client_id}
            if project_id is not None:
                altheader['X-Project-ID'] = project_id
            uri = self.topic_path + '/' + name
            self.simulate_put(uri, headers=altheader, body=body)

        create_topic('q1', project_id, '{"node": 31}')
        create_topic('q2', project_id, '{"node": 32}')
        create_topic('q3', project_id, '{"node": 33}')

        create_topic('q3', alt_project_id, '{"alt": 1}')

        # List (limit)
        result = self.simulate_get(self.topic_path, headers=header,
                                   query_string='limit=2')

        result_doc = jsonutils.loads(result[0])
        self.assertEqual(2, len(result_doc['topics']))

        # List (no metadata, get all)
        result = self.simulate_get(self.topic_path,
                                   headers=header, query_string='limit=5')

        result_doc = jsonutils.loads(result[0])
        [target, params] = result_doc['links'][0]['href'].split('?')
        self.simulate_get(target, headers=header, query_string=params)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        # Ensure we didn't pick up the topic from the alt project.
        topics = result_doc['topics']
        self.assertEqual(3, len(topics))

        # List with metadata
        result = self.simulate_get(self.topic_path, headers=header,
                                   query_string='detailed=true')

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        result_doc = jsonutils.loads(result[0])
        [target, params] = result_doc['links'][0]['href'].split('?')

        topic = result_doc['topics'][0]
        result = self.simulate_get(topic['href'], headers=header)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(topic['metadata'], result_doc)
        self.assertEqual({'node': 31, '_default_message_ttl': 3600,
                          '_max_messages_post_size': 262144,
                          '_default_message_delay': 0}, result_doc)

        # topic filter
        result = self.simulate_get(self.topic_path, headers=header,
                                   query_string='node=34')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(0, len(result_doc['topics']))

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

        topic_controller = self.boot.storage.topic_controller

        with mock.patch.object(topic_controller, 'list') as mock_topic_list:

            def topic_generator():
                raise storage_errors.NoPoolFound()

            # This generator tries to be like topic controller list generator
            # in some ways.
            def fake_generator():
                yield topic_generator()
                yield {}
            mock_topic_list.return_value = fake_generator()
            self.simulate_get(self.topic_path, headers=header)
            self.assertEqual(falcon.HTTP_503, self.srmock.status)

    def test_list_with_filter(self):
        arbitrary_number = 644079696574693
        project_id = str(arbitrary_number)
        client_id = uuidutils.generate_uuid()
        header = {
            'X-Project-ID': project_id,
            'Client-ID': client_id
        }

        # Create some
        def create_topic(name, project_id, body):
            altheader = {'Client-ID': client_id}
            if project_id is not None:
                altheader['X-Project-ID'] = project_id
            uri = self.topic_path + '/' + name
            self.simulate_put(uri, headers=altheader, body=body)

        create_topic('q1', project_id, '{"test_metadata_key1": "value1"}')
        create_topic('q2', project_id, '{"_max_messages_post_size": 2000}')
        create_topic('q3', project_id, '{"test_metadata_key2": 30}')

        # List (filter query)
        result = self.simulate_get(self.topic_path, headers=header,
                                   query_string='name=q&test_metadata_key2=30')

        result_doc = jsonutils.loads(result[0])
        self.assertEqual(1, len(result_doc['topics']))
        self.assertEqual('q3', result_doc['topics'][0]['name'])

        # List (filter query)
        result = self.simulate_get(self.topic_path, headers=header,
                                   query_string='_max_messages_post_size=2000')

        result_doc = jsonutils.loads(result[0])
        self.assertEqual(1, len(result_doc['topics']))
        self.assertEqual('q2', result_doc['topics'][0]['name'])

        # List (filter query)
        result = self.simulate_get(self.topic_path, headers=header,
                                   query_string='name=q')

        result_doc = jsonutils.loads(result[0])
        self.assertEqual(3, len(result_doc['topics']))


class TestTopicLifecycleFaultyDriver(base.V2BaseFaulty):

    config_file = 'wsgi_faulty.conf'

    def test_simple(self):
        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': '338730984abc_1'
        }

        mars_topic_path = self.url_prefix + '/topics/mars'
        doc = '{"messages": {"ttl": 600}}'
        self.simulate_put(mars_topic_path,
                          headers=self.headers,
                          body=doc)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        location = ('Location', mars_topic_path)
        self.assertNotIn(location, self.srmock.headers)

        result = self.simulate_get(mars_topic_path,
                                   headers=self.headers)
        result_doc = jsonutils.loads(result[0])
        self.assertEqual(falcon.HTTP_503, self.srmock.status)
        self.assertNotEqual(result_doc, jsonutils.loads(doc))

        self.simulate_get(mars_topic_path + '/stats',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_get(self.url_prefix + '/topics',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

        self.simulate_delete(mars_topic_path, headers=self.headers)
        self.assertEqual(falcon.HTTP_503, self.srmock.status)

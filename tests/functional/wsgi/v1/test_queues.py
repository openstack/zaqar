# -*- coding: utf-8 -*-
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
# See the License for the specific language governing permissions and
# limitations under the License.
import copy
import ddt
import uuid

from marconi.tests.functional import base  # noqa


@ddt.ddt
class TestInsertQueue(base.FunctionalTestBase):
    """Tests for Insert queue."""

    server_class = base.MarconiServer

    def setUp(self):
        super(TestInsertQueue, self).setUp()
        self.base_url = '%s/%s' % (self.cfg.marconi.url,
                                   self.cfg.marconi.version)

        self.headers_response_empty = set(['location'])
        self.client.set_base_url(self.base_url)

    @ddt.data('qtestqueue', 'TESTqueue', 'hyphen-name', '_undersore',
              'i' * 64)
    def test_insert_queue(self, queue_name):
        """Create Queue."""
        self.url = self.base_url + '/queues/' + queue_name

        result = self.client.put(self.url)
        self.assertEqual(result.status_code, 201)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_empty, response_headers)

        self.url = self.url + '/metadata'
        result = self.client.get(self.url)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {})

    test_insert_queue.tags = ['positive', 'smoke']

    @ddt.data('汉字漢字', '@$@^qw', 'i' * 65)
    def test_insert_queue_invalid_name(self, queue_name):
        """Create Queue."""
        self.url = self.base_url + '/queues/' + queue_name
        self.skipTest("Test fails, needs fix")

        result = self.client.put(self.url)
        self.assertEqual(result.status_code, 400)

        self.url = self.url + '/metadata'
        result = self.client.get(self.url)
        self.assertEqual(result.status_code, 404)

    test_insert_queue_invalid_name.tags = ['negative']

    def test_insert_queue_invalid_authtoken(self):
        """Insert Queue with invalid authtoken."""

        # NOTE(flaper87): Currently, tearDown
        # depends on this attribute. Needs to
        # be fixed.
        self.url = self.base_url + '/queues/invalidauthtoken'

        if not self.cfg.auth.auth_on:
            self.skipTest("Auth is not on!")

        header = copy.copy(self.header)
        header["X-Auth-Token"] = 'invalid'

        result = self.client.put(self.url, header)
        self.assertEqual(result.status_code, 401)

    test_insert_queue_invalid_authtoken.tags = ['negative']

    def test_insert_queue_header_plaintext(self):
        """Insert Queue with 'Accept': 'plain/text'."""
        path = '/queues/plaintextheader'
        self.addCleanup(self.client.delete, path)

        header = {"Accept": 'plain/text'}
        result = self.client.put(path, headers=header)
        self.assertEqual(result.status_code, 406)

    test_insert_queue_header_plaintext.tags = ['negative']

    def test_insert_queue_header_asterisk(self):
        """Insert Queue with 'Accept': '*/*'."""
        path = '/queues/asteriskinheader'
        self.addCleanup(self.client.delete, path)

        header = {"Accept": '*/*'}
        result = self.client.put(path, headers=header)
        self.assertEqual(result.status_code, 201)

    test_insert_queue_header_asterisk.tags = ['positive']

    def test_insert_queue_with_metadata(self):
        """Insert queue with a non-empty request body."""
        self.url = self.base_url + '/queues/hasmetadata'
        doc = {"queue": "Has Metadata"}
        result = self.client.put(self.url, data=doc)

        self.assertEqual(result.status_code, 201)

        self.url = self.base_url + '/queues/hasmetadata/metadata'
        result = self.client.get(self.url)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {})

    test_insert_queue_with_metadata.tags = ['negative']

    def tearDown(self):
        super(TestInsertQueue, self).tearDown()


@ddt.ddt
class TestQueueMetaData(base.FunctionalTestBase):
    """Tests for queue metadata."""

    server_class = base.MarconiServer

    def setUp(self):
        super(TestQueueMetaData, self).setUp()

        self.base_url = '%s/%s' % (self.cfg.marconi.url,
                                   self.cfg.marconi.version)

        self.queue_url = self.base_url + '/queues/{0}'.format(uuid.uuid1())
        self.client.put(self.queue_url)

        self.queue_metadata_url = self.queue_url + '/metadata'
        self.client.set_base_url(self.queue_metadata_url)

    @ddt.data({},
              {"_queue": "Top Level field with _"},
              {"汉字": "non ASCII metadata"},
              {"queue": "#$%^&Apple"},
              {"queue": "i" * 65000}
              )
    def test_insert_queue_metadata(self, doc):
        """Insert Queue with empty json."""
        self.skipTest("Test fails, needs fix")
        result = self.client.put(data=doc)
        self.assertEqual(result.status_code, 204)

        result = self.client.get()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), doc)

    test_insert_queue_metadata.tags = ['smoke', 'positive']

    @ddt.data('not_a_dict', {"queue": "i" * 65537})
    def test_insert_queue_invalid_metadata(self, doc):
        """Insert invalid metadata."""

        result = self.client.put(data=doc)
        self.assertEqual(result.status_code, 400)

    test_insert_queue_invalid_metadata.tags = ['negative']

    def tearDown(self):
        super(TestQueueMetaData, self).tearDown()
        self.client.delete(self.queue_url)


@ddt.ddt
class TestQueueMisc(base.FunctionalTestBase):

    server_class = base.MarconiServer

    def setUp(self):
        super(TestQueueMisc, self).setUp()

        self.base_url = '%s/%s' % (self.cfg.marconi.url,
                                   self.cfg.marconi.version)

        self.client.set_base_url(self.base_url)

    def test_list_queues(self):
        """List Queues."""

        result = self.client.get('/queues')
        self.assertEqual(result.status_code, 200)

        response_keys = result.json().keys()
        for key in ['links', 'queues']:
            self.assertIn(key, response_keys)

    test_list_queues.tags = ['smoke', 'positive']

    def test_list_queues_detailed(self):
        """List Queues with detailed = True."""

        params = {'detailed': True}
        result = self.client.get('/queues', params=params)
        self.assertEqual(result.status_code, 200)

        response_keys = result.json()['queues'][0].keys()
        for key in ['href', 'metadata', 'name']:
            self.assertIn(key, response_keys)

    test_list_queues_detailed.tags = ['smoke', 'positive']

    @ddt.data(0, -1, 30)
    def test_list_queue_invalid_limit(self, limit):
        """List Queues with a limit value that is not allowed."""

        params = {'limit': limit}
        result = self.client.get('/queues', params=params)
        self.assertEqual(result.status_code, 400)

    test_list_queue_invalid_limit.tags = ['negative']

    def test_check_health(self):
        """Test health endpoint."""

        result = self.client.get('/health')
        self.assertEqual(result.status_code, 204)

    test_check_health.tags = ['positive']

    def test_check_queue_exists(self):
        """Checks if queue exists."""

        path = '/queues/testqueue'
        self.client.put(path)
        result = self.client.get(path)
        self.assertEqual(result.status_code, 204)

        result = self.client.head(path)
        self.assertEqual(result.status_code, 204)

    test_check_queue_exists.tags = ['positive']

    def test_check_queue_exists_negative(self):
        """Checks non-existing queue."""
        path = '/queues/nonexistingqueue'
        result = self.client.get(path)
        self.assertEqual(result.status_code, 404)

        result = self.client.head(path)
        self.assertEqual(result.status_code, 404)

    test_check_queue_exists_negative.tags = ['negative']

    def test_get_queue_malformed_marker(self):
        """List queues with invalid marker."""
        self.skipTest("Test fails, needs fix")

        url = self.base_url + '/queues?marker=invalid'
        result = self.client.get(url)
        self.assertEqual(result.status_code, 204)

    test_get_queue_malformed_marker.tags = ['negative']

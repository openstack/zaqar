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
import json
import uuid

from marconi.tests.functional import base  # noqa
from marconi.tests.functional import http


@ddt.ddt
class TestInsertQueue(base.FunctionalTestBase):
    """Tests for Insert queue."""

    server_class = base.MarconiServer

    def setUp(self):
        super(TestInsertQueue, self).setUp()
        self.base_url = '%s/%s' % (self.cfg.marconi.url,
                                   self.cfg.marconi.version)

        self.headers_response_empty = set(['location'])

    @ddt.data('qtestqueue', 'TESTqueue', 'hyphen-name', '_undersore',
              'i' * 64)
    def test_insert_queue(self, queue_name):
        """Create Queue."""
        self.url = self.base_url + '/queues/' + queue_name

        result = http.put(self.url, self.header)
        self.assertEqual(result.status_code, 201)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_empty, response_headers)

        self.url = self.url + '/metadata'
        result = http.get(self.url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {})

    test_insert_queue.tags = ['positive', 'smoke']

    @ddt.data('汉字漢字', '@$@^qw', 'i' * 65)
    def test_insert_queue_invalid_name(self, queue_name):
        """Create Queue."""
        self.url = self.base_url + '/queues/' + queue_name
        self.skipTest("Test fails, needs fix")

        result = http.put(self.url, self.header)
        self.assertEqual(result.status_code, 400)

        self.url = self.url + '/metadata'
        result = http.get(self.url, self.header)
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

        result = http.put(self.url, header)
        self.assertEqual(result.status_code, 401)

    test_insert_queue_invalid_authtoken.tags = ['negative']

    def test_insert_queue_header_plaintext(self):
        """Insert Queue with 'Accept': 'plain/text'."""
        self.url = self.base_url + '/queues/plaintextheader'
        header = copy.copy(self.header)
        header["Accept"] = 'plain/text'

        result = http.put(self.url, header)
        self.assertEqual(result.status_code, 406)

    test_insert_queue_header_plaintext.tags = ['negative']

    def test_insert_queue_header_asterisk(self):
        """Insert Queue with 'Accept': '*/*'."""
        self.url = self.base_url + '/queues/asteriskinheader'
        header = copy.copy(self.header)
        header["Accept"] = '*/*'

        result = http.put(self.url, header)
        self.assertEqual(result.status_code, 201)

    test_insert_queue_header_asterisk.tags = ['positive']

    def test_insert_queue_with_metadata(self):
        """Insert queue with a non-empty request body."""
        self.url = self.base_url + '/queues/hasmetadata'
        doc = '{"queue": "Has Metadata"}'
        result = http.put(self.url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        self.url = self.base_url + '/queues/hasmetadata/metadata'
        result = http.get(self.url, self.header)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {})

    test_insert_queue_with_metadata.tags = ['negative']

    def tearDown(self):
        super(TestInsertQueue, self).tearDown()
        http.delete(self.url, self.header)


@ddt.ddt
class TestQueueMetaData(base.FunctionalTestBase):
    """Tests for queue metadata."""

    server_class = base.MarconiServer

    def setUp(self):
        super(TestQueueMetaData, self).setUp()

        self.base_url = '%s/%s' % (self.cfg.marconi.url,
                                   self.cfg.marconi.version)

        self.queue_url = self.base_url + '/queues/{0}'.format(uuid.uuid1())
        http.put(self.queue_url, self.header)

        self.queue_metadata_url = self.queue_url + '/metadata'

    @ddt.data({},
              {"_queue": "Top Level field with _"},
              {"汉字": "non ASCII metadata"},
              {"queue": "#$%^&Apple"},
              {"queue": "i" * 65000}
              )
    def test_insert_queue_metadata(self, doc):
        """Insert Queue with empty json."""
        self.skipTest("Test fails, needs fix")
        result = http.put(self.queue_metadata_url, self.header,
                          json.dumps(doc))
        self.assertEqual(result.status_code, 204)

        result = http.get(self.queue_metadata_url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), doc)

    test_insert_queue_metadata.tags = ['smoke', 'positive']

    @ddt.data('not_a_dict',
              {"queue": "i" * 65537}
              )
    def test_insert_queue_invalid_metadata(self, doc):
        """Insert invalid metadata."""

        result = http.put(self.queue_metadata_url, self.header, str(doc))
        self.assertEqual(result.status_code, 400)

    test_insert_queue_invalid_metadata.tags = ['negative']

    def tearDown(self):
        super(TestQueueMetaData, self).tearDown()
        http.delete(self.queue_url, self.header)


@ddt.ddt
class TestQueueMisc(base.FunctionalTestBase):

    server_class = base.MarconiServer

    def setUp(self):
        super(TestQueueMisc, self).setUp()

        self.base_url = '%s/%s' % (self.cfg.marconi.url,
                                   self.cfg.marconi.version)

    def test_list_queues(self):
        """List Queues."""
        url = self.base_url + '/queues'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 200)

        response_keys_actual = result.json().keys()
        response_keys_actual.sort()
        response_keys_expected = ['links', 'queues']
        self.assertEqual(response_keys_actual, response_keys_expected)

    test_list_queues.tags = ['smoke', 'positive']

    def test_list_queues_detailed(self):
        """List Queues with detailed = True."""
        url = self.base_url + '/queues?detailed=True'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 200)

        response_keys_actual = result.json()['queues'][0].keys()
        response_keys_actual.sort()
        response_keys_expected = ['href', 'metadata', 'name']
        self.assertEqual(response_keys_actual, response_keys_expected)

    test_list_queues_detailed.tags = ['smoke', 'positive']

    @ddt.data(0, -1, 30)
    def test_list_queue_invalid_limit(self, limit):
        """List Queues with a limit value that is not allowed."""
        url = self.base_url + '/queues?limit=' + str(limit)
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 400)

    test_list_queue_invalid_limit.tags = ['negative']

    def test_check_health(self):
        """Test health endpoint."""
        url = self.base_url + '/health'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 204)

    test_check_health.tags = ['positive']

    def test_check_queue_exists(self):
        """Checks if queue exists."""
        url = self.base_url + '/queues/testqueue'
        http.put(url, self.header)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 204)

        result = http.head(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_check_queue_exists.tags = ['positive']

    def test_check_queue_exists_negative(self):
        """Checks non-existing queue."""
        url = self.base_url + '/queues/nonexistingqueue'

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

        result = http.head(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_check_queue_exists_negative.tags = ['negative']

    def test_get_queue_malformed_marker(self):
        """List queues with invalid marker."""
        url = self.base_url + '/queues?marker=invalid'
        self.skipTest("Test fails, needs fix")

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_get_queue_malformed_marker.tags = ['negative']

    @classmethod
    def tearDownClass(cls):
        """Delete Queue."""
        url = cls.base_url + '/queues/testqueue'
        http.delete(url, cls.header)

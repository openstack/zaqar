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
from marconi.tests.system.common import config
from marconi.tests.system.common import functionlib
from marconi.tests.system.common import http
from marconi.tests.system.queue import queuefnlib

import json


class TestQueue(functionlib.TestUtils):
    """Tests for queue."""

    def setUp(self):
        super(TestQueue, self).setUp()
        self.cfg = config.Config()
        self.header = functionlib.create_marconi_headers()

        self.headers_response_empty = set(['location'])
        self.headers_response_with_body = set(['content-location',
                                               'content-type'])

    def test_001_queue_insert(self):
        """Insert Queue.

        Creates Queue, does a get & verifies data.
        """
        url = self.cfg.base_url + '/queues/qtestqueue'
        doc = '{"queue": "Apple"}'
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_empty, response_headers)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        self.assertEqual(result.json(), json.loads(doc))

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_with_body, response_headers)

    test_001_queue_insert.tags = ['smoke', 'positive', 'create_queue']

    def test_002_queue_insert_case_insensitive(self):
        """Insert Queue with same name, different case."""
        url = self.cfg.base_url + '/queues/QteStquEue'
        doc = '{"queue": "Orange"}'

        result = http.put(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), json.loads(doc))

        http.delete(url, self.header)

    test_002_queue_insert_case_insensitive.tags = ['positive']

    def test_003_queue_update_empty_metadata(self):
        """Update Queue with empty metadata."""
        url = self.cfg.base_url + '/queues/qtestqueue'
        doc_original = '{"queue": "Apple"}'
        doc = ''

        result = http.put(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), json.loads(doc_original))

    test_003_queue_update_empty_metadata.tags = ['negative']

    def test_004_queue_update_empty_json(self):
        """Update Queue with empty json."""
        url = self.cfg.base_url + '/queues/qtestqueue'
        doc = '{}'

        result = http.put(url, self.header, doc)
        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), json.loads(doc))

    test_004_queue_update_empty_json.tags = ['smoke', 'positive']

    def test_005_queue_insert_invalid_authtoken(self):
        """Insert Queue with invalid authtoken."""
        url = self.cfg.base_url + '/queues/invalidauthtoken'
        header = functionlib.invalid_auth_token_header()
        doc = '{"queue": "invalid auth token"}'

        result = http.put(url, header, doc)
        self.assertEqual(result.status_code, 401)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_005_queue_insert_invalid_authtoken.tags = ['negative']

    def test_006_queue_update_invalid_authtoken(self):
        """Update Queue with invalid authtoken."""
        url = self.cfg.base_url + '/queues/qtestqueue'
        header = functionlib.invalid_auth_token_header()
        doc = '{"queue": "invalid auth token"}'
        doc_original = '{}'

        result = http.put(url, header, doc)
        self.assertEqual(result.status_code, 401)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), json.loads(doc_original))

    test_006_queue_update_invalid_authtoken.tags = ['negative']

    def test_007_queue_insert_missing_header(self):
        """Insert Queue with missing header field.

        Request has no Accept header.
        """
        url = self.cfg.base_url + '/queues/missingheader'
        header = functionlib.missing_header_fields()
        doc = '{"queue": "Accept header is missing"}'

        result = http.put(url, header, doc)
        self.assertEqual(result.status_code, 400)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_007_queue_insert_missing_header.tags = ['negative']

    def test_008_queue_insert_toplevel_underscore(self):
        """Insert Queue with underscore in toplevel field."""
        url = self.cfg.base_url + '/queues/toplevel'
        doc = '{"_queue": "Top Level field with _"}'

        result = http.put(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_008_queue_insert_toplevel_underscore.tags = ['negative']

    def test_009_queue_insert_header_plaintext(self):
        """Insert Queue with 'Accept': 'plain/text'."""
        url = self.cfg.base_url + '/queues/plaintextheader'
        header = functionlib.plain_text_in_header()
        doc = '{"queue": "text/plain in header"}'

        result = http.put(url, header, doc)
        self.assertEqual(result.status_code, 406)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_009_queue_insert_header_plaintext.tags = ['negative']

    def test_010_queue_insert_header_asterisk(self):
        """Insert Queue with 'Accept': '*/*'."""
        url = self.cfg.base_url + '/queues/asteriskinheader'
        header = functionlib.asterisk_in_header()
        doc = '{"queue": "*/* in header"}'

        result = http.put(url, header, doc)
        self.assertEqual(result.status_code, 201)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        http.delete(url, self.header)

    test_010_queue_insert_header_asterisk.tags = ['positive']

    def test_011_queue_insert_nonASCII_name(self):
        """Insert Queue with non ASCII name."""
        url = self.cfg.base_url + '/queues/汉字/漢字'
        doc = '{"queue": "non ASCII name"}'

        result = http.put(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_011_queue_insert_nonASCII_name.tags = ['negative']

    def test_012_queue_insert_nonASCII_metadata(self):
        """Insert Queue with non ASCII name."""
        url = self.cfg.base_url + '/queues/nonASCIImetadata'
        doc = '{"汉字": "non ASCII metadata"}'

        result = http.put(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_012_queue_insert_nonASCII_metadata.tags = ['negative']

    def test_013_queue_update_metadata_size4095(self):
        """Updates Queue with metadata_size = 4095."""
        url = self.cfg.base_url + '/queues/qtestqueue'
        doc = functionlib.get_custom_body({"metadatasize": 4095})
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), json.loads(doc))

    test_013_queue_update_metadata_size4095.tags = ['positive']

    def test_014_queue_update_metadata_size4096(self):
        """Updates Queue with metadata_size = 4096."""
        url = self.cfg.base_url + '/queues/qtestqueue'
        doc = functionlib.get_custom_body({"metadatasize": 4096})
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), json.loads(doc))

    test_014_queue_update_metadata_size4096.tags = ['positive']

    def test_015_queue_update_metadata_size4097(self):
        """Updates Queue with metadata_size = 4097."""
        url = self.cfg.base_url + '/queues/qtestqueue'
        doc = functionlib.get_custom_body({"metadatasize": 4097})
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 400)

    test_015_queue_update_metadata_size4097.tags = ['negative']

    def test_016_queue_insert_long_queuename(self):
        """Insert queue with name > 64 bytes."""
        url = self.cfg.base_url + queuefnlib.get_queue_name()
        doc = '{"queue": "Longer than allowed queue name"}'
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 400)

    test_016_queue_insert_long_queuename.tags = ['negative']

    def test_017_queue_stats(self):
        """Insert queue with name > 64 bytes."""
        url = self.cfg.base_url + '/queues/qtestqueue/stats'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 200)

        test_result_flag = queuefnlib.verify_queue_stats(result.headers,
                                                         result.text)
        self.assertEqual(test_result_flag, True)

    test_017_queue_stats.tags = ['smoke', 'positive']

    def test_018_queue_list(self):
        """List Queues."""
        url = self.cfg.base_url + '/queues'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 200)

        test_result_flag = queuefnlib.verify_list_queues(result.headers,
                                                         result.text)
        self.assertEqual(test_result_flag, True)

    test_018_queue_list.tags = ['smoke', 'positive']

    def test_019_queue_list_detailed(self):
        """List Queues with detailed = True."""
        url = self.cfg.base_url + '/queues?detailed=True'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 200)

        test_result_flag = queuefnlib.verify_list_queues(result.headers,
                                                         result.text)
        self.assertEqual(test_result_flag, True)

    test_019_queue_list_detailed.tags = ['smoke', 'positive']

    def test_020_queue_insert_metadata_invalidchar(self):
        """Update Queues with invalid char in metadata."""
        url = self.cfg.base_url + '/queues/qtestqueue'
        doc = '{"queue": "#$%^&Apple"}'
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 400)

    test_020_queue_insert_metadata_invalidchar.tags = ['negative']

    def test_021_queue_get_nonexisting(self):
        """Update Queues with invalid char in metadata."""
        url = self.cfg.base_url + '/queues/nonexistingqueue'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 404)

    test_021_queue_get_nonexisting.tags = ['negative']

    def test_022_check_health(self):
        """Test health endpoint."""
        url = self.cfg.base_url + '/health'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 204)

    test_022_check_health.tags = ['positive']

    def test_999_delete_queue(self):
        """Delete Queue.

        Deletes Queue & performs GET to confirm 404.
        """
        url = self.cfg.base_url + '/queues/qtestqueue'

        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 404)

    test_999_delete_queue.tags = ['smoke']

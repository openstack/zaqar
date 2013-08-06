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

    def test_001_insert_queue(self):
        """Create Queue."""
        url = self.cfg.base_url + '/queues/qtestqueue'

        result = http.put(url, self.header)
        self.assertEqual(result.status_code, 201)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_empty, response_headers)

        url = self.cfg.base_url + '/queues/qtestqueue/metadata'
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {})

        http.delete(url, self.header)

    test_001_insert_queue.tags = ['smoke', 'positive', 'create_queue']

    def test_002_insert_queue_case_insensitive(self):
        """Insert Queue with same name, different case."""
        url = self.cfg.base_url + '/queues/QteStquEue'

        result = http.put(url, self.header)
        self.assertEqual(result.status_code, 201)

        http.delete(url, self.header)

    test_002_insert_queue_case_insensitive.tags = ['positive']

    def test_003_insert_queue_empty_json(self):
        """Update Queue with empty json."""
        url = self.cfg.base_url + '/queues/emptyjson'
        doc = '{}'

        result = http.put(url, self.header, doc)
        self.assertEqual(result.status_code, 201)

        http.delete(url, self.header)

    test_003_insert_queue_empty_json.tags = ['smoke', 'positive']

    def test_004_insert_queue_invalid_authtoken(self):
        """Insert Queue with invalid authtoken."""
        url = self.cfg.base_url + '/queues/invalidauthtoken'
        header = functionlib.invalid_auth_token_header()

        result = http.put(url, header)
        self.assertEqual(result.status_code, 401)

    test_004_insert_queue_invalid_authtoken.tags = ['negative']

    def test_005_insert_queue_missing_header(self):
        """Insert Queue with missing header field.

        Request has no Accept header.
        """
        header = functionlib.missing_header_fields()

        url = self.cfg.base_url + '/queues/missingheader'
        http.put(url, header)

        url = self.cfg.base_url + '/queues/missingheader/metadata'
        doc = '{"queue": "Missing Header"}'

        result = http.put(url, header, doc)
        self.assertEqual(result.status_code, 400)

        url = self.cfg.base_url + '/queues/missingheader'
        http.delete(url, self.header)

    test_005_insert_queue_missing_header.tags = ['negative']

    def test_006_insert_queue_header_plaintext(self):
        """Insert Queue with 'Accept': 'plain/text'."""
        url = self.cfg.base_url + '/queues/plaintextheader'
        header = functionlib.plain_text_in_header()

        result = http.put(url, header)
        self.assertEqual(result.status_code, 406)

        http.delete(url, self.header)

    test_006_insert_queue_header_plaintext.tags = ['negative']

    def test_007_insert_queue_header_asterisk(self):
        """Insert Queue with 'Accept': '*/*'."""
        url = self.cfg.base_url + '/queues/asteriskinheader'
        header = functionlib.asterisk_in_header()

        result = http.put(url, header)
        self.assertEqual(result.status_code, 201)

        http.delete(url, self.header)

    test_007_insert_queue_header_asterisk.tags = ['positive']

    def test_008_insert_queue_nonASCII_name(self):
        """Insert Queue with non ASCII name."""
        url = self.cfg.base_url + '/queues/汉字漢字'
        doc = '{"queue": "non ASCII name"}'

        result = http.put(url, self.header, doc)
        self.assertEqual(result.status_code, 400)

    test_008_insert_queue_nonASCII_name.tags = ['negative']

    def test_009_insert_queue_long_queuename(self):
        """Insert queue with name > 64 bytes."""
        url = self.cfg.base_url + queuefnlib.get_queue_name()
        result = http.put(url, self.header)

        self.assertEqual(result.status_code, 400)

    test_009_insert_queue_long_queuename.tags = ['negative']

    def test_010_insert_queue_hyphenated_queuename(self):
        """Insert queue with hyphen in name."""
        url = self.cfg.base_url + '/queues/hyphen-name'
        result = http.put(url, self.header)

        self.assertEqual(result.status_code, 201)

        http.delete(url, self.header)

    test_010_insert_queue_hyphenated_queuename.tags = ['positive']

    def test_011_insert_queue_invalid_char(self):
        """Insert queue with invalid characters in name."""
        url = self.cfg.base_url + '/queues/@$@^qw)'
        result = http.put(url, self.header)

        self.assertEqual(result.status_code, 400)

    test_011_insert_queue_invalid_char.tags = ['negative']

    def test_012_insert_queue_with_metadata(self):
        """Insert queue with a non-empty request body."""
        url = self.cfg.base_url + '/queues/hasmetadata'
        doc = '{"queue": "Has Metadata"}'
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 201)

        url = self.cfg.base_url + '/queues/hasmetadata/metadata'
        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {})

        url = self.cfg.base_url + '/queues/hasmetadata'
        http.delete(url, self.header)

    test_012_insert_queue_with_metadata.tags = ['negative']

    def test_013_queue_metadata_invalid_authtoken(self):
        """Update Queue with invalid authtoken."""
        url = self.cfg.base_url + '/queues/qtestqueue/metadata'
        header = functionlib.invalid_auth_token_header()
        doc = '{"queue": "invalid auth token"}'

        result = http.put(url, header, doc)
        self.assertEqual(result.status_code, 401)

    test_013_queue_metadata_invalid_authtoken.tags = ['negative']

    def test_014_queue_metadata_toplevel_underscore(self):
        """Insert Queue with underscore in toplevel field."""
        url = self.cfg.base_url + '/queues/toplevel'
        result = http.put(url, self.header)

        url = self.cfg.base_url + '/queues/toplevel/metadata'
        doc = '{"_queue": "Top Level field with _"}'

        result = http.put(url, self.header, doc)
        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), json.loads(doc))

        url = self.cfg.base_url + '/queues/toplevel'
        http.delete(url, self.header)

    test_014_queue_metadata_toplevel_underscore.tags = ['negative']

    def test_015_queue_insert_nonASCII_metadata(self):
        """Insert Queue with non ASCII name."""
        url = self.cfg.base_url + '/queues/nonASCIImetadata'
        result = http.put(url, self.header)

        url = self.cfg.base_url + '/queues/nonASCIImetadata/metadata'
        doc = '{"汉字": "non ASCII metadata"}'
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)

        url = self.cfg.base_url + '/queues/nonASCIImetadata'
        result = http.delete(url, self.header)

    test_015_queue_insert_nonASCII_metadata.tags = ['negative']

    def test_016_queue_insert_metadata_size65535(self):
        """Updates Queue with metadata_size = 65535."""
        url = self.cfg.base_url + '/queues/qtestqueue'
        result = http.put(url, self.header)

        url = self.cfg.base_url + '/queues/qtestqueue/metadata'
        doc = functionlib.get_custom_body({"metadatasize": 65535})
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), json.loads(doc))

    test_016_queue_insert_metadata_size65535.tags = ['positive']

    def test_017_queue_insert_metadata_size65536(self):
        """Updates Queue with metadata_size = 65536."""
        url = self.cfg.base_url + '/queues/qtestqueue/metadata'
        doc = functionlib.get_custom_body({"metadatasize": 65536})
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 204)

        result = http.get(url, self.header)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), json.loads(doc))

    test_017_queue_insert_metadata_size65536.tags = ['positive']

    def test_018_queue_insert_metadata_size65537(self):
        """Updates Queue with metadata_size = 65537."""
        url = self.cfg.base_url + '/queues/qtestqueue/metadata'
        doc = functionlib.get_custom_body({"metadatasize": 65537})
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 400)

    test_018_queue_insert_metadata_size65537.tags = ['negative']

    def test_019_queue_insert_metadata_invalidchar(self):
        """Update Queues with invalid char in metadata."""
        url = self.cfg.base_url + '/queues/qtestqueue/metadata'
        doc = '{"queue": "#$%^&Apple"}'
        result = http.put(url, self.header, doc)

        self.assertEqual(result.status_code, 204)

        url = self.cfg.base_url + '/queues/qtestqueue'
        result = http.delete(url, self.header)

    test_019_queue_insert_metadata_invalidchar.tags = ['negative']

    def test_020_queue_stats(self):
        """Insert queue with name > 64 bytes."""
        url = self.cfg.base_url + '/queues/qtestqueue/stats'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 200)

        test_result_flag = queuefnlib.verify_queue_stats(result.headers,
                                                         result.text)
        self.assertEqual(test_result_flag, True)

    test_020_queue_stats.tags = ['smoke', 'positive']

    def test_021_queue_list(self):
        """List Queues."""
        url = self.cfg.base_url + '/queues'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 200)

        test_result_flag = queuefnlib.verify_list_queues(result.headers,
                                                         result.text)
        self.assertEqual(test_result_flag, True)

    test_021_queue_list.tags = ['smoke', 'positive']

    def test_022_queue_list_detailed(self):
        """List Queues with detailed = True."""
        url = self.cfg.base_url + '/queues?detailed=True'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 200)

        test_result_flag = queuefnlib.verify_list_queues(result.headers,
                                                         result.text)
        self.assertEqual(test_result_flag, True)

    test_022_queue_list_detailed.tags = ['smoke', 'positive']

    def test_023_check_health(self):
        """Test health endpoint."""
        url = self.cfg.base_url + '/health'
        result = http.get(url, self.header)

        self.assertEqual(result.status_code, 204)

    test_023_check_health.tags = ['positive']

    def test_999_delete_queue(self):
        """Delete Queue.

        Deletes Queue & performs GET to confirm 404.
        """
        url = self.cfg.base_url + '/queues/qtestqueue'

        result = http.delete(url, self.header)
        self.assertEqual(result.status_code, 204)

    test_999_delete_queue.tags = ['smoke']

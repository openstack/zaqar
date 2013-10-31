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
import uuid

import ddt
import six

from marconi.tests.functional import base  # noqa
from marconi.tests.functional import helpers


class NamedBinaryStr(six.binary_type):

    """Wrapper for six.binary_type to facilitate overriding __name__."""


class NamedUnicodeStr(object):

    """Unicode string look-alike to facilitate overriding __name__."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def encode(self, enc):
        return self.value.encode(enc)

    def __format__(self, formatstr):
        """Workaround for ddt bug.

        DDT will always call __format__ even when __name__ exists,
        which blows up for Unicode strings under Py2.
        """
        return ''


class NamedDict(dict):

    """Wrapper for dict to facilitate overriding __name__."""


def annotated(test_name, test_input):
    if isinstance(test_input, dict):
        annotated_input = NamedDict(test_input)
    elif isinstance(test_input, six.text_type):
        annotated_input = NamedUnicodeStr(test_input)
    else:
        annotated_input = NamedBinaryStr(test_input)

    setattr(annotated_input, '__name__', test_name)
    return annotated_input


@ddt.ddt
class TestInsertQueue(base.FunctionalTestBase):

    """Tests for Insert queue."""

    server_class = base.MarconiServer

    def setUp(self):
        super(TestInsertQueue, self).setUp()
        self.base_url = '{0}/{1}'.format(self.cfg.marconi.url,
                                         self.cfg.marconi.version)

        self.header = helpers.create_marconi_headers(self.cfg)
        self.headers_response_empty = set(['location'])
        self.client.set_base_url(self.base_url)
        self.header = helpers.create_marconi_headers(self.cfg)

    @ddt.data('qtestqueue', 'TESTqueue', 'hyphen-name', '_undersore',
              annotated('test_insert_queue_long_name', 'i' * 64))
    def test_insert_queue(self, queue_name):
        """Create Queue."""
        self.url = self.base_url + '/queues/' + queue_name
        self.addCleanup(self.client.delete, self.url)

        result = self.client.put(self.url)
        self.assertEqual(result.status_code, 201)

        response_headers = set(result.headers.keys())
        self.assertIsSubset(self.headers_response_empty, response_headers)

        self.url = self.url + '/metadata'
        result = self.client.get(self.url)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {})

    test_insert_queue.tags = ['positive', 'smoke']

    @ddt.data(annotated('test_insert_queue_non_ascii_name',
                        u'\u6c49\u5b57\u6f22\u5b57'),
              '@$@^qw',
              annotated('test_insert_queue_invalid_name_length', 'i' * 65))
    def test_insert_queue_invalid_name(self, queue_name):
        """Create Queue."""
        if six.PY2 and isinstance(queue_name, NamedUnicodeStr):
            queue_name = queue_name.encode('utf-8')

        self.url = self.base_url + '/queues/' + queue_name
        self.addCleanup(self.client.delete, self.url)

        result = self.client.put(self.url)
        self.assertEqual(result.status_code, 400)

        self.url = self.url + '/metadata'
        result = self.client.get(self.url)
        self.assertEqual(result.status_code, 400)

    test_insert_queue_invalid_name.tags = ['negative']

    def test_insert_queue_invalid_authtoken(self):
        """Insert Queue with invalid authtoken."""

        # NOTE(flaper87): Currently, tearDown
        # depends on this attribute. Needs to
        # be fixed.
        self.url = self.base_url + '/queues/invalidauthtoken'
        self.addCleanup(self.client.delete, self.url)

        if not self.cfg.auth.auth_on:
            self.skipTest("Auth is not on!")

        header = copy.copy(self.header)
        header['X-Auth-Token'] = 'invalid'

        result = self.client.put(self.url, headers=header)
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
        self.addCleanup(self.client.delete, self.url)
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

        self.base_url = '{0}/{1}'.format(self.cfg.marconi.url,
                                         self.cfg.marconi.version)

        self.queue_url = self.base_url + '/queues/{0}'.format(uuid.uuid1())
        self.client.put(self.queue_url)

        self.queue_metadata_url = self.queue_url + '/metadata'
        self.client.set_base_url(self.queue_metadata_url)

    @ddt.data({},
              {'_queue': 'Top Level field with _'},
              annotated('test_insert_queue_metadata_unicode', {
                  u'\u6c49\u5b57': u'Unicode: \u6c49\u5b57'
              }),
              {'queue': '#$%^&Apple'},
              annotated('test_insert_queue_metadata_huge',
                        {"queue": "i" * 65000}))
    def test_insert_queue_metadata(self, doc):
        """Insert Queue with empty json."""
        result = self.client.put(data=doc)
        self.assertEqual(result.status_code, 204)

        result = self.client.get()
        self.assertEqual(result.status_code, 200)

        doc_decoded = {}
        for k, v in doc.items():
            if isinstance(k, six.binary_type):
                k = k.decode('utf-8')

            if isinstance(v, six.binary_type):
                v = v.decode('utf-8')

            doc_decoded[k] = v

        self.assertEqual(result.json(), doc_decoded)

    test_insert_queue_metadata.tags = ['smoke', 'positive']

    @ddt.data('not_a_dict',
              annotated('test_insert_queue_invalid_metadata_huge',
                        {"queue": "i" * 65537}))
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

        self.base_url = self.cfg.marconi.url
        self.client.set_base_url(self.base_url)

        self.queue_url = self.base_url + '/{0}/queues/{1}' \
                                         .format(self.cfg.marconi.version,
                                                 uuid.uuid1())

    def test_list_queues(self):
        """List Queues."""

        self.client.put(self.queue_url)
        self.addCleanup(self.client.delete, self.queue_url)

        result = self.client.get('/{0}/queues'
                                 .format(self.cfg.marconi.version))
        self.assertEqual(result.status_code, 200)

        response_keys = result.json().keys()
        for key in ['links', 'queues']:
            self.assertIn(key, response_keys)

    test_list_queues.tags = ['smoke', 'positive']

    def test_list_queues_detailed(self):
        """List Queues with detailed = True."""

        self.client.put(self.queue_url)
        self.addCleanup(self.client.delete, self.queue_url)

        params = {'detailed': True}
        result = self.client.get('/{0}/queues'
                                 .format(self.cfg.marconi.version),
                                 params=params)
        self.assertEqual(result.status_code, 200)

        response_keys = result.json()['queues'][0].keys()
        for key in ['href', 'metadata', 'name']:
            self.assertIn(key, response_keys)

    test_list_queues_detailed.tags = ['smoke', 'positive']

    @ddt.data(0, -1, 1001)
    def test_list_queue_invalid_limit(self, limit):
        """List Queues with a limit value that is not allowed."""

        params = {'limit': limit}
        result = self.client.get('/{0}/queues'
                                 .format(self.cfg.marconi.version),
                                 params=params)
        self.assertEqual(result.status_code, 400)

    test_list_queue_invalid_limit.tags = ['negative']

    def test_check_health(self):
        """Test health endpoint."""

        result = self.client.get('/{0}/health'
                                 .format(self.cfg.marconi.version))
        self.assertEqual(result.status_code, 204)

    test_check_health.tags = ['positive']

    def test_check_queue_exists(self):
        """Checks if queue exists."""

        self.client.put(self.queue_url)
        self.addCleanup(self.client.delete, self.queue_url)
        result = self.client.get(self.queue_url)
        self.assertEqual(result.status_code, 204)

        result = self.client.head(self.queue_url)
        self.assertEqual(result.status_code, 204)

    test_check_queue_exists.tags = ['positive']

    def test_check_queue_exists_negative(self):
        """Checks non-existing queue."""
        path = '/{0}/queues/nonexistingqueue'.format(self.cfg.marconi.version)
        result = self.client.get(path)
        self.assertEqual(result.status_code, 404)

        result = self.client.head(path)
        self.assertEqual(result.status_code, 404)

    test_check_queue_exists_negative.tags = ['negative']

    def test_get_queue_malformed_marker(self):
        """List queues with invalid marker."""

        path = '/{0}/queues?marker=zzz'.format(self.cfg.marconi.version)
        result = self.client.get(path)
        self.assertEqual(result.status_code, 204)

    test_get_queue_malformed_marker.tags = ['negative']

    def test_get_stats_empty_queue(self):
        """Get queue stats on an empty queue."""

        result = self.client.put(self.queue_url)
        self.addCleanup(self.client.delete, self.queue_url)
        self.assertEqual(result.status_code, 201)

        stats_url = self.queue_url + '/stats'

        # Get stats on an empty queue
        result = self.client.get(stats_url)
        self.assertEqual(result.status_code, 200)

        expected_response = {'messages':
                             {'claimed': 0, 'total': 0, 'free': 0}}
        self.assertEqual(result.json(), expected_response)

    test_get_stats_empty_queue.tags = ['positive']

    @ddt.data(0, 1)
    def test_get_queue_stats_claimed(self, claimed):
        """Get stats on a queue."""
        result = self.client.put(self.queue_url)
        self.addCleanup(self.client.delete, self.queue_url)
        self.assertEqual(result.status_code, 201)

        # Post Messages to the test queue
        doc = helpers.create_message_body(messagecount=
                                          self.limits.message_paging_uplimit)
        message_url = self.queue_url + '/messages'
        result = self.client.post(message_url, data=doc)
        self.assertEqual(result.status_code, 201)

        if claimed > 0:
            claim_url = self.queue_url + '/claims?limit=' + str(claimed)
            doc = {'ttl': 300, 'grace': 300}
            result = self.client.post(claim_url, data=doc)
            self.assertEqual(result.status_code, 201)

        # Get stats on the queue.
        stats_url = self.queue_url + '/stats'
        result = self.client.get(stats_url)
        self.assertEqual(result.status_code, 200)

        self.assertQueueStats(result.json(), claimed)

    test_get_queue_stats_claimed.tags = ['positive']

    def tearDown(self):
        super(TestQueueMisc, self).tearDown()


class TestQueueNonExisting(base.FunctionalTestBase):

    """Test Actions on non existing queue."""

    server_class = base.MarconiServer

    def setUp(self):
        super(TestQueueNonExisting, self).setUp()
        self.base_url = '{0}/{1}'.format(self.cfg.marconi.url,
                                         self.cfg.marconi.version)
        self.queue_url = self.base_url + \
            '/queues/0a5b1b85-4263-11e3-b034-28cfe91478b9'
        self.client.set_base_url(self.queue_url)

        self.header = helpers.create_marconi_headers(self.cfg)
        self.headers_response_empty = set(['location'])
        self.header = helpers.create_marconi_headers(self.cfg)

    def test_get_queue(self):
        """Get non existing Queue."""
        result = self.client.get()
        self.assertEqual(result.status_code, 404)

    def test_get_stats(self):
        """Get stats on non existing Queue."""
        result = self.client.get('/stats')
        self.assertEqual(result.status_code, 404)

    def test_get_metadata(self):
        """Get metadata on non existing Queue."""
        result = self.client.get('/metadata')
        self.assertEqual(result.status_code, 404)

    def test_get_messages(self):
        """Get messages on non existing Queue."""
        result = self.client.get('/messages')
        self.assertEqual(result.status_code, 204)

    def test_post_messages(self):
        """Post messages to a non existing Queue."""
        doc = [{"ttl": 200, "body": {"Home": ""}}]
        result = self.client.post('/messages', data=doc)
        self.assertEqual(result.status_code, 404)

    def test_claim_messages(self):
        """Claim messages from a non existing Queue."""
        doc = {"ttl": 200, "grace": 300}
        result = self.client.post('/claims', data=doc)
        self.assertEqual(result.status_code, 204)

    def test_delete_queue(self):
        """Delete non existing Queue."""
        result = self.client.delete()
        self.assertEqual(result.status_code, 204)

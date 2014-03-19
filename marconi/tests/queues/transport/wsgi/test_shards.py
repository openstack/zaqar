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

import contextlib
import json
import uuid

import ddt
import falcon

from . import base  # noqa
from marconi import tests as testing


@contextlib.contextmanager
def shard(test, name, weight, uri, options={}):
    """A context manager for constructing a shard for use in testing.

    Deletes the shard after exiting the context.

    :param test: Must expose simulate_* methods
    :param name: Name for this shard
    :type name: six.text_type
    :type weight: int
    :type uri: six.text_type
    :type options: dict
    :returns: (name, weight, uri, options)
    :rtype: see above
    """
    doc = {'weight': weight, 'uri': uri, 'options': options}
    path = test.url_prefix + '/shards/' + name

    test.simulate_put(path, body=json.dumps(doc))

    try:
        yield name, weight, uri, options

    finally:
        test.simulate_delete(path)


@contextlib.contextmanager
def shards(test, count, uri):
    """A context manager for constructing shards for use in testing.

    Deletes the shards after exiting the context.

    :param test: Must expose simulate_* methods
    :param count: Number of shards to create
    :type count: int
    :returns: (paths, weights, uris, options)
    :rtype: ([six.text_type], [int], [six.text_type], [dict])
    """
    base = test.url_prefix + '/shards/'
    args = [(base + str(i), i,
             {str(i): i})
            for i in range(count)]
    for path, weight, option in args:
        doc = {'weight': weight, 'uri': uri, 'options': option}
        test.simulate_put(path, body=json.dumps(doc))

    try:
        yield args
    finally:
        for path, _, _ in args:
            test.simulate_delete(path)


@ddt.ddt
class ShardsBaseTest(base.TestBase):

    def setUp(self):
        super(ShardsBaseTest, self).setUp()
        self.doc = {'weight': 100, 'uri': 'sqlite://:memory:'}
        self.shard = self.url_prefix + '/shards/' + str(uuid.uuid1())
        self.simulate_put(self.shard, body=json.dumps(self.doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def tearDown(self):
        super(ShardsBaseTest, self).tearDown()
        self.simulate_delete(self.shard)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def test_put_shard_works(self):
        name = str(uuid.uuid1())
        weight, uri = self.doc['weight'], self.doc['uri']
        with shard(self, name, weight, uri):
            self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def test_put_raises_if_missing_fields(self):
        path = self.url_prefix + '/shards/' + str(uuid.uuid1())
        self.simulate_put(path, body=json.dumps({'weight': 100}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_put(path, body=json.dumps({'uri': 'sqlite://:memory:'}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 2**32+1, 'big')
    def test_put_raises_if_invalid_weight(self, weight):
        path = self.url_prefix + '/shards/' + str(uuid.uuid1())
        doc = {'weight': weight, 'uri': 'a'}
        self.simulate_put(path,
                          body=json.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 2**32+1, [], 'localhost:27017')
    def test_put_raises_if_invalid_uri(self, uri):
        path = self.url_prefix + '/shards/' + str(uuid.uuid1())
        self.simulate_put(path,
                          body=json.dumps({'weight': 1, 'uri': uri}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 'wee', [])
    def test_put_raises_if_invalid_options(self, options):
        path = self.url_prefix + '/shards/' + str(uuid.uuid1())
        doc = {'weight': 1, 'uri': 'a', 'options': options}
        self.simulate_put(path, body=json.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_put_existing_overwrites(self):
        # NOTE(cabrera): setUp creates default shard
        expect = self.doc
        self.simulate_put(self.shard,
                          body=json.dumps(expect))
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        result = self.simulate_get(self.shard)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        doc = json.loads(result[0])
        self.assertEqual(doc['weight'], expect['weight'])
        self.assertEqual(doc['uri'], expect['uri'])

    def test_delete_works(self):
        self.simulate_delete(self.shard)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        self.simulate_get(self.shard)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_get_nonexisting_raises_404(self):
        self.simulate_get(self.url_prefix + '/shards/nonexisting')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def _shard_expect(self, shard, xhref, xweight, xuri):
        self.assertIn('href', shard)
        self.assertEqual(shard['href'], xhref)
        self.assertIn('weight', shard)
        self.assertEqual(shard['weight'], xweight)
        self.assertIn('uri', shard)
        self.assertEqual(shard['uri'], xuri)

    def test_get_works(self):
        result = self.simulate_get(self.shard)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        shard = json.loads(result[0])
        self._shard_expect(shard, self.shard, self.doc['weight'],
                           self.doc['uri'])

    def test_detailed_get_works(self):
        result = self.simulate_get(self.shard,
                                   query_string='?detailed=True')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        shard = json.loads(result[0])
        self._shard_expect(shard, self.shard, self.doc['weight'],
                           self.doc['uri'])
        self.assertIn('options', shard)
        self.assertEqual(shard['options'], {})

    def test_patch_raises_if_missing_fields(self):
        self.simulate_patch(self.shard,
                            body=json.dumps({'location': 1}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def _patch_test(self, doc):
        self.simulate_patch(self.shard,
                            body=json.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        result = self.simulate_get(self.shard,
                                   query_string='?detailed=True')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        shard = json.loads(result[0])
        self._shard_expect(shard, self.shard, doc['weight'],
                           doc['uri'])
        self.assertEqual(shard['options'], doc['options'])

    def test_patch_works(self):
        doc = {'weight': 101, 'uri': 'sqlite://:memory:', 'options': {'a': 1}}
        self._patch_test(doc)

    def test_patch_works_with_extra_fields(self):
        doc = {'weight': 101, 'uri': 'sqlite://:memory:', 'options': {'a': 1},
               'location': 100, 'partition': 'taco'}
        self._patch_test(doc)

    @ddt.data(-1, 2**32+1, 'big')
    def test_patch_raises_400_on_invalid_weight(self, weight):
        self.simulate_patch(self.shard,
                            body=json.dumps({'weight': weight}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 2**32+1, [], 'localhost:27017')
    def test_patch_raises_400_on_invalid_uri(self, uri):
        self.simulate_patch(self.shard,
                            body=json.dumps({'uri': uri}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 'wee', [])
    def test_patch_raises_400_on_invalid_options(self, options):
        self.simulate_patch(self.shard,
                            body=json.dumps({'options': options}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_patch_raises_404_if_shard_not_found(self):
        self.simulate_patch(self.url_prefix + '/shards/notexists',
                            body=json.dumps({'weight': 1}))
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_empty_listing_returns_204(self):
        self.simulate_delete(self.shard)
        self.simulate_get(self.url_prefix + '/shards')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def _listing_test(self, count=10, limit=10,
                      marker=None, detailed=False):
        # NOTE(cpp-cabrera): delete initial shard - it will interfere
        # with listing tests
        self.simulate_delete(self.shard)
        query = '?limit={0}&detailed={1}'.format(limit, detailed)
        if marker:
            query += '&marker={2}'.format(marker)

        with shards(self, count, self.doc['uri']) as expected:
            result = self.simulate_get(self.url_prefix + '/shards',
                                       query_string=query)
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            results = json.loads(result[0])
            self.assertIsInstance(results, dict)
            self.assertIn('shards', results)
            shard_list = results['shards']
            self.assertEqual(len(shard_list), min(limit, count))
            for s in shard_list:
                # NOTE(flwang): It can't assumed that both sqlalchemy and
                # mongodb can return query result with the same order. Just
                # like the order they're inserted. Actually, sqlalchemy can't
                # guarantee that. So we're leveraging the relationship between
                # shard weight and the index of shards fixture to get the
                # right shard to verify.
                expect = expected[s['weight']]
                path, weight = expect[:2]
                self._shard_expect(s, path, weight, self.doc['uri'])
                if detailed:
                    self.assertIn('options', s)
                    self.assertEqual(s['options'], expect[-1])
                else:
                    self.assertNotIn('options', s)

    def test_listing_works(self):
        self._listing_test()

    def test_detailed_listing_works(self):
        self._listing_test(detailed=True)

    @ddt.data(1, 5, 10, 15)
    def test_listing_works_with_limit(self, limit):
        self._listing_test(count=15, limit=limit)

    def test_listing_marker_is_respected(self):
        self.simulate_delete(self.shard)

        with shards(self, 10, self.doc['uri']) as expected:
            result = self.simulate_get(self.url_prefix + '/shards',
                                       query_string='?marker=3')
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            shard_list = json.loads(result[0])['shards']
            self.assertEqual(len(shard_list), 6)
            path, weight = expected[4][:2]
            self._shard_expect(shard_list[0], path, weight, self.doc['uri'])


class TestShardsMongoDB(ShardsBaseTest):

    config_file = 'wsgi_mongodb.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestShardsMongoDB, self).setUp()


class TestShardsSqlalchemy(ShardsBaseTest):

    config_file = 'wsgi_sqlalchemy.conf'

    def setUp(self):
        super(TestShardsSqlalchemy, self).setUp()

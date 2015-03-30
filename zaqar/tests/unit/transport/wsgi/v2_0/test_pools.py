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
import uuid

import ddt
import falcon
from oslo_serialization import jsonutils

from zaqar import tests as testing
from zaqar.tests.unit.transport.wsgi import base


@contextlib.contextmanager
def pool(test, name, weight, uri, group=None, options={}):
    """A context manager for constructing a pool for use in testing.

    Deletes the pool after exiting the context.

    :param test: Must expose simulate_* methods
    :param name: Name for this pool
    :type name: six.text_type
    :type weight: int
    :type uri: six.text_type
    :type options: dict
    :returns: (name, weight, uri, options)
    :rtype: see above
    """
    uri = "%s/%s" % (uri, str(uuid.uuid4()))
    doc = {'weight': weight, 'uri': uri,
           'group': group, 'options': options}
    path = test.url_prefix + '/pools/' + name

    test.simulate_put(path, body=jsonutils.dumps(doc))

    try:
        yield name, weight, uri, group, options

    finally:
        test.simulate_delete(path)


@contextlib.contextmanager
def pools(test, count, uri, group):
    """A context manager for constructing pools for use in testing.

    Deletes the pools after exiting the context.

    :param test: Must expose simulate_* methods
    :param count: Number of pools to create
    :type count: int
    :returns: (paths, weights, uris, options)
    :rtype: ([six.text_type], [int], [six.text_type], [dict])
    """
    base = test.url_prefix + '/pools/'
    args = [(base + str(i), i,
             {str(i): i})
            for i in range(count)]
    for path, weight, option in args:
        uri = "%s/%s" % (uri, str(uuid.uuid4()))
        doc = {'weight': weight, 'uri': uri,
               'group': group, 'options': option}
        test.simulate_put(path, body=jsonutils.dumps(doc))

    try:
        yield args
    finally:
        for path, _, _ in args:
            test.simulate_delete(path)


@ddt.ddt
class PoolsBaseTest(base.V2Base):

    def setUp(self):
        super(PoolsBaseTest, self).setUp()
        self.doc = {'weight': 100,
                    'group': 'mygroup',
                    'uri': 'mongodb://127.0.0.1:27017'}
        self.pool = self.url_prefix + '/pools/' + str(uuid.uuid1())
        self.simulate_put(self.pool, body=jsonutils.dumps(self.doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def tearDown(self):
        super(PoolsBaseTest, self).tearDown()
        self.simulate_delete(self.pool)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

    def test_put_pool_works(self):
        name = str(uuid.uuid1())
        weight, uri = self.doc['weight'], self.doc['uri']
        with pool(self, name, weight, uri, group='my-group'):
            self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def test_put_raises_if_missing_fields(self):
        path = self.url_prefix + '/pools/' + str(uuid.uuid1())
        self.simulate_put(path, body=jsonutils.dumps({'weight': 100}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_put(path,
                          body=jsonutils.dumps(
                              {'uri': 'mongodb://127.0.0.1:27017'}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 2**32+1, 'big')
    def test_put_raises_if_invalid_weight(self, weight):
        path = self.url_prefix + '/pools/' + str(uuid.uuid1())
        doc = {'weight': weight, 'uri': 'a'}
        self.simulate_put(path,
                          body=jsonutils.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 2**32+1, [], 'localhost:27017')
    def test_put_raises_if_invalid_uri(self, uri):
        path = self.url_prefix + '/pools/' + str(uuid.uuid1())
        self.simulate_put(path,
                          body=jsonutils.dumps({'weight': 1, 'uri': uri}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 'wee', [])
    def test_put_raises_if_invalid_options(self, options):
        path = self.url_prefix + '/pools/' + str(uuid.uuid1())
        doc = {'weight': 1, 'uri': 'a', 'options': options}
        self.simulate_put(path, body=jsonutils.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_put_existing_overwrites(self):
        # NOTE(cabrera): setUp creates default pool
        expect = self.doc
        self.simulate_put(self.pool,
                          body=jsonutils.dumps(expect))
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        result = self.simulate_get(self.pool)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        doc = jsonutils.loads(result[0])
        self.assertEqual(doc['weight'], expect['weight'])
        self.assertEqual(doc['uri'], expect['uri'])

    def test_delete_works(self):
        self.simulate_delete(self.pool)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        self.simulate_get(self.pool)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_get_nonexisting_raises_404(self):
        self.simulate_get(self.url_prefix + '/pools/nonexisting')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def _pool_expect(self, pool, xhref, xweight, xuri):
        self.assertIn('href', pool)
        self.assertEqual(pool['href'], xhref)
        self.assertIn('weight', pool)
        self.assertEqual(pool['weight'], xweight)
        self.assertIn('uri', pool)

        # NOTE(dynarro): we are using startwith because we are adding to
        # pools UUIDs, to avoid dupplications
        self.assertTrue(pool['uri'].startswith(xuri))

    def test_get_works(self):
        result = self.simulate_get(self.pool)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        pool = jsonutils.loads(result[0])
        self._pool_expect(pool, self.pool, self.doc['weight'],
                          self.doc['uri'])

    def test_detailed_get_works(self):
        result = self.simulate_get(self.pool,
                                   query_string='?detailed=True')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        pool = jsonutils.loads(result[0])
        self._pool_expect(pool, self.pool, self.doc['weight'],
                          self.doc['uri'])
        self.assertIn('options', pool)
        self.assertEqual(pool['options'], {})

    def test_patch_raises_if_missing_fields(self):
        self.simulate_patch(self.pool,
                            body=jsonutils.dumps({'location': 1}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def _patch_test(self, doc):
        self.simulate_patch(self.pool,
                            body=jsonutils.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        result = self.simulate_get(self.pool,
                                   query_string='?detailed=True')
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        pool = jsonutils.loads(result[0])
        self._pool_expect(pool, self.pool, doc['weight'],
                          doc['uri'])
        self.assertEqual(pool['options'], doc['options'])

    def test_patch_works(self):
        doc = {'weight': 101,
               'uri': 'mongodb://localhost:27017',
               'options': {'a': 1}}
        self._patch_test(doc)

    def test_patch_works_with_extra_fields(self):
        doc = {'weight': 101,
               'uri': 'mongodb://localhost:27017',
               'options': {'a': 1},
               'location': 100,
               'partition': 'taco'}
        self._patch_test(doc)

    @ddt.data(-1, 2**32+1, 'big')
    def test_patch_raises_400_on_invalid_weight(self, weight):
        self.simulate_patch(self.pool,
                            body=jsonutils.dumps({'weight': weight}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 2**32+1, [], 'localhost:27017')
    def test_patch_raises_400_on_invalid_uri(self, uri):
        self.simulate_patch(self.pool,
                            body=jsonutils.dumps({'uri': uri}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 'wee', [])
    def test_patch_raises_400_on_invalid_options(self, options):
        self.simulate_patch(self.pool,
                            body=jsonutils.dumps({'options': options}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_patch_raises_404_if_pool_not_found(self):
        self.simulate_patch(self.url_prefix + '/pools/notexists',
                            body=jsonutils.dumps({'weight': 1}))
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_empty_listing(self):
        self.simulate_delete(self.pool)
        result = self.simulate_get(self.url_prefix + '/pools')
        results = jsonutils.loads(result[0])
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertTrue(len(results['pools']) == 0)
        self.assertIn('links', results)

    def _listing_test(self, count=10, limit=10,
                      marker=None, detailed=False):
        # NOTE(cpp-cabrera): delete initial pool - it will interfere
        # with listing tests
        self.simulate_delete(self.pool)
        query = '?limit={0}&detailed={1}'.format(limit, detailed)
        if marker:
            query += '&marker={0}'.format(marker)

        with pools(self, count, self.doc['uri'], 'my-group') as expected:
            result = self.simulate_get(self.url_prefix + '/pools',
                                       query_string=query)
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            results = jsonutils.loads(result[0])
            self.assertIsInstance(results, dict)
            self.assertIn('pools', results)
            self.assertIn('links', results)
            pool_list = results['pools']

            link = results['links'][0]
            self.assertEqual('next', link['rel'])
            href = falcon.uri.parse_query_string(link['href'])
            self.assertIn('marker', href)
            self.assertEqual(href['limit'], str(limit))
            self.assertEqual(href['detailed'], str(detailed).lower())

            next_query_string = ('?marker={marker}&limit={limit}'
                                 '&detailed={detailed}').format(**href)
            next_result = self.simulate_get(link['href'].split('?')[0],
                                            query_string=next_query_string)
            self.assertEqual(self.srmock.status, falcon.HTTP_200)

            next_pool = jsonutils.loads(next_result[0])
            next_pool_list = next_pool['pools']

            self.assertIn('links', next_pool)
            if limit < count:
                self.assertEqual(len(next_pool_list),
                                 min(limit, count-limit))
            else:
                # NOTE(jeffrey4l): when limit >= count, there will be no
                # pools in the 2nd page.
                self.assertTrue(len(next_pool_list) == 0)

            self.assertEqual(len(pool_list), min(limit, count))
            for s in pool_list + next_pool_list:
                # NOTE(flwang): It can't assumed that both sqlalchemy and
                # mongodb can return query result with the same order. Just
                # like the order they're inserted. Actually, sqlalchemy can't
                # guarantee that. So we're leveraging the relationship between
                # pool weight and the index of pools fixture to get the
                # right pool to verify.
                expect = expected[s['weight']]
                path, weight, group = expect[:3]
                self._pool_expect(s, path, weight, self.doc['uri'])
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
        self.simulate_delete(self.pool)

        with pools(self, 10, self.doc['uri'], 'my-group') as expected:
            result = self.simulate_get(self.url_prefix + '/pools',
                                       query_string='?marker=3')
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            pool_list = jsonutils.loads(result[0])['pools']
            self.assertEqual(len(pool_list), 6)
            path, weight = expected[4][:2]
            self._pool_expect(pool_list[0], path, weight, self.doc['uri'])


class TestPoolsMongoDB(PoolsBaseTest):

    config_file = 'wsgi_mongodb_pooled.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestPoolsMongoDB, self).setUp()


class TestPoolsSqlalchemy(PoolsBaseTest):

    config_file = 'wsgi_sqlalchemy_pooled.conf'

    def setUp(self):
        super(TestPoolsSqlalchemy, self).setUp()

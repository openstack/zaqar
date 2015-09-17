# Copyright (c) 2014 Red Hat, Inc.
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
def flavor(test, name, pool):
    """A context manager for constructing a flavor for use in testing.

    Deletes the flavor after exiting the context.

    :param test: Must expose simulate_* methods
    :param name: Name for this flavor
    :type name: six.text_type
    :type pool: six.text_type
    :returns: (name, uri, capabilities)
    :rtype: see above

    """

    doc = {'pool': pool}
    path = test.url_prefix + '/flavors/' + name

    test.simulate_put(path, body=jsonutils.dumps(doc))

    try:
        yield name, pool

    finally:
        test.simulate_delete(path)


@contextlib.contextmanager
def flavors(test, count, pool):
    """A context manager for constructing flavors for use in testing.

    Deletes the flavors after exiting the context.

    :param test: Must expose simulate_* methods
    :param count: Number of pools to create
    :type count: int
    :returns: (paths, pool, capabilities)
    :rtype: ([six.text_type], [six.text_type], [dict])

    """

    base = test.url_prefix + '/flavors/'
    args = sorted([(base + str(i), str(i)) for i in range(count)],
                  key=lambda tup: tup[1])
    for path, _ in args:
        doc = {'pool': pool}
        test.simulate_put(path, body=jsonutils.dumps(doc))

    try:
        yield args
    finally:
        for path, _ in args:
            test.simulate_delete(path)


@ddt.ddt
class TestFlavorsMongoDB(base.V2Base):

    config_file = 'wsgi_mongodb_pooled.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestFlavorsMongoDB, self).setUp()
        self.queue = 'test-queue'
        self.queue_path = self.url_prefix + '/queues/' + self.queue

        self.pool = 'mypool'
        self.pool_group = 'mypool-group'
        self.pool_path = self.url_prefix + '/pools/' + self.pool
        self.pool_doc = {'weight': 100,
                         'group': self.pool_group,
                         'uri': self.mongodb_url + '/test'}
        self.simulate_put(self.pool_path, body=jsonutils.dumps(self.pool_doc))

        self.flavor = 'test-flavor'
        self.doc = {'capabilities': {}, 'pool': self.pool_group}
        self.flavor_path = self.url_prefix + '/flavors/' + self.flavor
        self.simulate_put(self.flavor_path, body=jsonutils.dumps(self.doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def tearDown(self):
        self.simulate_delete(self.queue_path)
        self.simulate_delete(self.flavor_path)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.simulate_delete(self.pool_path)

        super(TestFlavorsMongoDB, self).tearDown()

    def test_put_flavor_works(self):
        name = str(uuid.uuid1())
        with flavor(self, name, self.doc['pool']):
            self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def test_put_raises_if_missing_fields(self):
        path = self.url_prefix + '/flavors/' + str(uuid.uuid1())
        self.simulate_put(path, body=jsonutils.dumps({}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        self.simulate_put(path,
                          body=jsonutils.dumps({'capabilities': {}}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(1, 2**32+1, [])
    def test_put_raises_if_invalid_pool(self, pool):
        path = self.url_prefix + '/flavors/' + str(uuid.uuid1())
        self.simulate_put(path,
                          body=jsonutils.dumps({'pool': pool}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 'wee', [])
    def test_put_raises_if_invalid_capabilities(self, capabilities):
        path = self.url_prefix + '/flavors/' + str(uuid.uuid1())
        doc = {'pool': 'a', 'capabilities': capabilities}
        self.simulate_put(path, body=jsonutils.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_put_existing_overwrites(self):
        # NOTE(cabrera): setUp creates default flavor
        expect = self.doc
        self.simulate_put(self.flavor_path,
                          body=jsonutils.dumps(expect))
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        result = self.simulate_get(self.flavor_path)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        doc = jsonutils.loads(result[0])
        self.assertEqual(doc['pool'], expect['pool'])

    def test_create_flavor_no_pool(self):
        self.simulate_delete(self.flavor_path)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        self.simulate_delete(self.pool_path)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        resp = self.simulate_put(self.flavor_path,
                                 body=jsonutils.dumps(self.doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        self.assertEqual(
            {'description': 'Flavor test-flavor could not be created. '
                            'Pool mypool-group does not exist',
             'title': 'Unable to create'},
            jsonutils.loads(resp[0]))

    def test_delete_works(self):
        self.simulate_delete(self.flavor_path)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        self.simulate_get(self.flavor_path)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_get_nonexisting_raises_404(self):
        self.simulate_get(self.url_prefix + '/flavors/nonexisting')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def _flavor_expect(self, flavor, xhref, xpool):
        self.assertIn('href', flavor)
        self.assertIn('name', flavor)
        self.assertEqual(flavor['href'], xhref)
        self.assertIn('pool', flavor)
        self.assertEqual(flavor['pool'], xpool)

    def test_get_works(self):
        result = self.simulate_get(self.flavor_path)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        pool = jsonutils.loads(result[0])
        self._flavor_expect(pool, self.flavor_path, self.doc['pool'])

        store_caps = ['FIFO', 'CLAIMS', 'DURABILITY',
                      'AOD', 'HIGH_THROUGHPUT']
        self.assertEqual(pool['capabilities'], store_caps)

    def test_patch_raises_if_missing_fields(self):
        self.simulate_patch(self.flavor_path,
                            body=jsonutils.dumps({'location': 1}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def _patch_test(self, doc):
        self.simulate_patch(self.flavor_path,
                            body=jsonutils.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        result = self.simulate_get(self.flavor_path)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        pool = jsonutils.loads(result[0])
        self._flavor_expect(pool, self.flavor_path, doc['pool'])
        self.assertEqual(pool['capabilities'], doc['capabilities'])

    def test_patch_works(self):
        doc = {'pool': 'mypool', 'capabilities': []}
        self._patch_test(doc)

    def test_patch_works_with_extra_fields(self):
        doc = {'pool': 'mypool', 'capabilities': [],
               'location': 100, 'partition': 'taco'}
        self._patch_test(doc)

    @ddt.data(-1, 2**32+1, [])
    def test_patch_raises_400_on_invalid_pool(self, pool):
        self.simulate_patch(self.flavor_path,
                            body=jsonutils.dumps({'pool': pool}))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    @ddt.data(-1, 'wee', [])
    def test_patch_raises_400_on_invalid_capabilities(self, capabilities):
        doc = {'capabilities': capabilities}
        self.simulate_patch(self.flavor_path, body=jsonutils.dumps(doc))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_patch_raises_404_if_flavor_not_found(self):
        self.simulate_patch(self.url_prefix + '/flavors/notexists',
                            body=jsonutils.dumps({'pool': 'test'}))
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_empty_listing(self):
        self.simulate_delete(self.flavor_path)
        result = self.simulate_get(self.url_prefix + '/flavors')
        results = jsonutils.loads(result[0])
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertTrue(len(results['flavors']) == 0)
        self.assertIn('links', results)

    def _listing_test(self, count=10, limit=10,
                      marker=None, detailed=False):
        # NOTE(cpp-cabrera): delete initial flavor - it will interfere
        # with listing tests
        self.simulate_delete(self.flavor_path)
        query = 'limit={0}&detailed={1}'.format(limit, detailed)
        if marker:
            query += '&marker={2}'.format(marker)

        with flavors(self, count, self.doc['pool']) as expected:
            result = self.simulate_get(self.url_prefix + '/flavors',
                                       query_string=query)
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            results = jsonutils.loads(result[0])
            self.assertIsInstance(results, dict)
            self.assertIn('flavors', results)
            self.assertIn('links', results)
            flavors_list = results['flavors']

            link = results['links'][0]
            self.assertEqual('next', link['rel'])
            href = falcon.uri.parse_query_string(link['href'].split('?')[1])
            self.assertIn('marker', href)
            self.assertEqual(href['limit'], str(limit))
            self.assertEqual(href['detailed'], str(detailed).lower())

            next_query_string = ('marker={marker}&limit={limit}'
                                 '&detailed={detailed}').format(**href)
            next_result = self.simulate_get(link['href'].split('?')[0],
                                            query_string=next_query_string)
            next_flavors = jsonutils.loads(next_result[0])
            next_flavors_list = next_flavors['flavors']

            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            self.assertIn('links', next_flavors)
            if limit < count:
                self.assertEqual(len(next_flavors_list),
                                 min(limit, count-limit))
            else:
                self.assertTrue(len(next_flavors_list) == 0)

            self.assertEqual(len(flavors_list), min(limit, count))
            for i, s in enumerate(flavors_list + next_flavors_list):
                expect = expected[i]
                path = expect[0]
                capabilities = ['FIFO', 'CLAIMS', 'DURABILITY',
                                'AOD', 'HIGH_THROUGHPUT']
                self._flavor_expect(s, path, self.doc['pool'])
                if detailed:
                    self.assertIn('capabilities', s)
                    self.assertEqual(s['capabilities'], capabilities)
                else:
                    self.assertNotIn('capabilities', s)

    def test_listing_works(self):
        self._listing_test()

    def test_detailed_listing_works(self):
        self._listing_test(detailed=True)

    @ddt.data(1, 5, 10, 15)
    def test_listing_works_with_limit(self, limit):
        self._listing_test(count=15, limit=limit)

    def test_listing_marker_is_respected(self):
        self.simulate_delete(self.flavor_path)

        with flavors(self, 10, self.doc['pool']) as expected:
            result = self.simulate_get(self.url_prefix + '/flavors',
                                       query_string='marker=3')
            self.assertEqual(self.srmock.status, falcon.HTTP_200)
            flavor_list = jsonutils.loads(result[0])['flavors']
            self.assertEqual(len(flavor_list), 6)
            path, capabilities = expected[4][:2]
            self._flavor_expect(flavor_list[0], path, self.doc['pool'])

    def test_queue_create_works(self):
        metadata = {'_flavor': self.flavor}
        self.simulate_put(self.queue_path, body=jsonutils.dumps(metadata))
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def test_queue_create_no_flavor(self):
        metadata = {'_flavor': self.flavor}

        self.simulate_delete(self.flavor_path)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        self.simulate_put(self.queue_path, body=jsonutils.dumps(metadata))
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

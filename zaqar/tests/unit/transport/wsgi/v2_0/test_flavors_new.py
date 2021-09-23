# Copyright (c) 2017 ZTE Corporation.
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
def flavor(test, name, pool_list):
    """A context manager for constructing a flavor for use in testing.

    Deletes the flavor after exiting the context.

    :param test: Must expose simulate_* methods
    :param name: Name for this flavor
    :type name: str
    :type pool: str
    :returns: (name, uri, capabilities)
    :rtype: see above

    """

    doc = {'pool_list': pool_list}
    path = test.url_prefix + '/flavors/' + name

    test.simulate_put(path, body=jsonutils.dumps(doc))

    try:
        yield name, pool_list

    finally:
        test.simulate_delete(path)


@contextlib.contextmanager
def flavors(test, count):
    """A context manager for constructing flavors for use in testing.

    Deletes the flavors after exiting the context.

    :param test: Must expose simulate_* methods
    :param count: Number of pools to create
    :type count: int
    :returns: (paths, pool_list capabilities)
    :rtype: ([str], [str], [dict])

    """

    pool_path_all = []
    flavor_path_all = []
    for i in range(count):
        poolname = 'pool' + str(i)
        pool_doc = {'weight': 100,
                    'uri': test.mongodb_url + '/test' + str(i)}
        pool_path = test.url_prefix + '/pools/' + poolname
        test.simulate_put(pool_path, body=jsonutils.dumps(pool_doc))
        flavorname = str(i)
        flavor_path = test.url_prefix + "/flavors/" + flavorname
        flavor_doc = {'pool_list': [poolname]}
        test.simulate_put(flavor_path, body=jsonutils.dumps(flavor_doc))
        pool_path_all.append(pool_path)
        flavor_path_all.append(flavor_path)

    try:
        yield flavor_path_all
    finally:
        for path in flavor_path_all:
            test.simulate_delete(path)
        for path in pool_path_all:
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
        self.pool_path = self.url_prefix + '/pools/' + self.pool
        self.pool_doc = {'weight': 100,
                         'uri': self.mongodb_url + '/test'}
        self.simulate_put(self.pool_path, body=jsonutils.dumps(self.pool_doc))

        self.flavor = 'test-flavor'
        self.doc = {'capabilities': {}}
        self.doc['pool_list'] = [self.pool]
        self.flavor_path = self.url_prefix + '/flavors/' + self.flavor
        self.simulate_put(self.flavor_path, body=jsonutils.dumps(self.doc))
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def tearDown(self):
        self.simulate_delete(self.queue_path)
        self.simulate_delete(self.flavor_path)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)
        self.simulate_delete(self.pool_path)

        super(TestFlavorsMongoDB, self).tearDown()

    def test_put_flavor_works(self):
        name = str(uuid.uuid1())
        with flavor(self, name, self.doc['pool_list']):
            self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_put_raises_if_missing_fields(self):
        path = self.url_prefix + '/flavors/' + str(uuid.uuid1())
        self.simulate_put(path, body=jsonutils.dumps({}))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_put(path,
                          body=jsonutils.dumps({'capabilities': {}}))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data(1, 2**32+1, [])
    def test_put_raises_if_invalid_pool(self, pool_list):
        path = self.url_prefix + '/flavors/' + str(uuid.uuid1())
        self.simulate_put(path,
                          body=jsonutils.dumps({'pool_list': pool_list}))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_put_auto_get_capabilities(self):
        path = self.url_prefix + '/flavors/' + str(uuid.uuid1())
        doc = {'pool_list': self.doc['pool_list']}
        self.simulate_put(path, body=jsonutils.dumps(doc))
        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        # NOTE(gengchc2): Delete it, otherwise exist garbage flavor.
        self.simulate_delete(path)

    def test_put_existing_overwrites(self):
        # NOTE(cabrera): setUp creates default flavor
        expect = self.doc
        self.simulate_put(self.flavor_path,
                          body=jsonutils.dumps(expect))
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        result = self.simulate_get(self.flavor_path)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        doc = jsonutils.loads(result[0])
        self.assertEqual(expect['pool_list'], doc['pool_list'])

    def test_create_flavor_no_pool_list(self):
        self.simulate_delete(self.flavor_path)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.simulate_delete(self.pool_path)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)
        resp = self.simulate_put(self.flavor_path,
                                 body=jsonutils.dumps(self.doc))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        self.assertEqual(
            {'description': 'Flavor test-flavor could not be created, '
                            'error:Pool mypool does not exist',
             'title': 'Unable to create'},
            jsonutils.loads(resp[0]))

    def test_delete_works(self):
        self.simulate_delete(self.flavor_path)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.simulate_get(self.flavor_path)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_get_nonexisting_raises_404(self):
        self.simulate_get(self.url_prefix + '/flavors/nonexisting')
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def _flavor_expect(self, flavor, xhref, xpool_list=None):
        self.assertIn('href', flavor)
        self.assertIn('name', flavor)
        self.assertEqual(xhref, flavor['href'])
        if xpool_list is not None:
            self.assertIn('pool_list', flavor)
            self.assertEqual(xpool_list, flavor['pool_list'])

    def test_get_works(self):
        result = self.simulate_get(self.flavor_path)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        flavor = jsonutils.loads(result[0])
        self._flavor_expect(flavor, self.flavor_path, self.doc['pool_list'])

        store_caps = ['FIFO', 'CLAIMS', 'DURABILITY',
                      'AOD', 'HIGH_THROUGHPUT']
        self.assertEqual(store_caps, flavor['capabilities'])

    def test_patch_raises_if_missing_fields(self):
        self.simulate_patch(self.flavor_path,
                            body=jsonutils.dumps({'location': 1}))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def _patch_test(self, doc):
        result = self.simulate_patch(self.flavor_path,
                                     body=jsonutils.dumps(doc))
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        updated_flavor = jsonutils.loads(result[0])
        self._flavor_expect(updated_flavor, self.flavor_path)
        capabilities = ['FIFO', 'CLAIMS', 'DURABILITY', 'AOD',
                        'HIGH_THROUGHPUT']
        self.assertEqual(capabilities, updated_flavor['capabilities'])
        result = self.simulate_get(self.flavor_path)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        flavor = jsonutils.loads(result[0])
        self._flavor_expect(flavor, self.flavor_path)
        self.assertEqual(capabilities, flavor['capabilities'])

    def test_patch_works(self):
        doc = {'pool_list': self.doc['pool_list'], 'capabilities': []}
        self._patch_test(doc)

    def test_patch_works_with_extra_fields(self):
        doc = {'pool_list': self.doc['pool_list'], 'capabilities': [],
               'location': 100, 'partition': 'taco'}
        self._patch_test(doc)

    @ddt.data(-1, 2**32+1, [])
    def test_patch_raises_400_on_invalid_pool_list(self, pool_list):
        self.simulate_patch(self.flavor_path,
                            body=jsonutils.dumps({'pool_list': pool_list}))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data(-1, 'wee', [])
    def test_patch_raises_400_on_invalid_capabilities(self, capabilities):
        doc = {'capabilities': capabilities}
        self.simulate_patch(self.flavor_path, body=jsonutils.dumps(doc))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_patch_raises_404_if_flavor_not_found(self):
        self.simulate_patch(self.url_prefix + '/flavors/notexists',
                            body=jsonutils.dumps({'pool_list': ['test']}))
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_empty_listing(self):
        self.simulate_delete(self.flavor_path)
        result = self.simulate_get(self.url_prefix + '/flavors')
        results = jsonutils.loads(result[0])
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertEqual(0, len(results['flavors']))
        self.assertIn('links', results)

    def _listing_test(self, count=10, limit=10,
                      marker=None, detailed=False):
        # NOTE(cpp-cabrera): delete initial flavor - it will interfere
        # with listing tests
        self.simulate_delete(self.flavor_path)
        query = 'limit={0}&detailed={1}'.format(limit, detailed)
        if marker:
            query += '&marker={2}'.format(marker)

        with flavors(self, count):
            result = self.simulate_get(self.url_prefix + '/flavors',
                                       query_string=query)
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            results = jsonutils.loads(result[0])
            self.assertIsInstance(results, dict)
            self.assertIn('flavors', results)
            self.assertIn('links', results)
            flavors_list = results['flavors']
            link = results['links'][0]
            self.assertEqual('next', link['rel'])
            href = falcon.uri.parse_query_string(link['href'].split('?')[1])
            self.assertIn('marker', href)
            self.assertEqual(str(limit), href['limit'])
            self.assertEqual(str(detailed).lower(), href['detailed'])

            next_query_string = ('marker={marker}&limit={limit}'
                                 '&detailed={detailed}').format(**href)
            next_result = self.simulate_get(link['href'].split('?')[0],
                                            query_string=next_query_string)
            next_flavors = jsonutils.loads(next_result[0])
            next_flavors_list = next_flavors['flavors']

            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            self.assertIn('links', next_flavors)
            if limit < count:
                self.assertEqual(min(limit, count-limit),
                                 len(next_flavors_list))
            else:
                self.assertEqual(0, len(next_flavors_list))

            self.assertEqual(min(limit, count), len(flavors_list))
            for i, s in enumerate(flavors_list + next_flavors_list):
                capabilities = ['FIFO', 'CLAIMS', 'DURABILITY',
                                'AOD', 'HIGH_THROUGHPUT']
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

        with flavors(self, 10) as expected:
            result = self.simulate_get(self.url_prefix + '/flavors',
                                       query_string='marker=3')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            flavor_list = jsonutils.loads(result[0])['flavors']
            self.assertEqual(6, len(flavor_list))
            path = expected[4]
            self._flavor_expect(flavor_list[0], path)

    def test_listing_error_with_invalid_limit(self):
        self.simulate_delete(self.flavor_path)
        query = 'limit={0}&detailed={1}'.format(0, True)

        with flavors(self, 10):
            self.simulate_get(self.url_prefix + '/flavors', query_string=query)
            self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_queue_create_works(self):
        metadata = {'_flavor': self.flavor}
        self.simulate_put(self.queue_path, body=jsonutils.dumps(metadata))
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_queue_create_no_flavor(self):
        metadata = {'_flavor': self.flavor}

        self.simulate_delete(self.flavor_path)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.simulate_put(self.queue_path, body=jsonutils.dumps(metadata))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

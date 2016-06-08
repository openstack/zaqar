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
def flavor(test, name, pool_group, capabilities={}):
    """A context manager for constructing a flavor for use in testing.

    Deletes the flavor after exiting the context.

    :param test: Must expose simulate_* methods
    :param name: Name for this flavor
    :type name: six.text_type
    :type pool_group: six.text_type
    :type capabilities: dict
    :returns: (name, uri, capabilities)
    :rtype: see above

    """

    doc = {'pool_group': pool_group, 'capabilities': capabilities}
    path = test.url_prefix + '/flavors/' + name

    test.simulate_put(path, body=jsonutils.dumps(doc))

    try:
        yield name, pool_group, capabilities

    finally:
        test.simulate_delete(path)


@contextlib.contextmanager
def flavors(test, count, pool_group):
    """A context manager for constructing flavors for use in testing.

    Deletes the flavors after exiting the context.

    :param test: Must expose simulate_* methods
    :param count: Number of pools to create
    :type count: int
    :returns: (paths, pool_group, capabilities)
    :rtype: ([six.text_type], [six.text_type], [dict])

    """

    base = test.url_prefix + '/flavors/'
    args = sorted([(base + str(i), {str(i): i}, str(i)) for i in range(count)],
                  key=lambda tup: tup[2])
    for path, capabilities, _ in args:
        doc = {'pool_group': pool_group, 'capabilities': capabilities}
        test.simulate_put(path, body=jsonutils.dumps(doc))

    try:
        yield args
    finally:
        for path, _, _ in args:
            test.simulate_delete(path)


@ddt.ddt
class TestFlavorsMongoDB(base.V1_1Base):

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
                         'uri': self.mongodb_url}
        self.simulate_put(self.pool_path, body=jsonutils.dumps(self.pool_doc))

        self.flavor = 'test-flavor'
        self.doc = {'capabilities': {}, 'pool_group': self.pool_group}
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
        with flavor(self, name, self.doc['pool_group']):
            self.assertEqual(falcon.HTTP_201, self.srmock.status)

    def test_put_raises_if_missing_fields(self):
        path = self.url_prefix + '/flavors/' + str(uuid.uuid1())
        self.simulate_put(path, body=jsonutils.dumps({}))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        self.simulate_put(path,
                          body=jsonutils.dumps({'capabilities': {}}))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data(1, 2**32+1, [])
    def test_put_raises_if_invalid_pool(self, pool):
        path = self.url_prefix + '/flavors/' + str(uuid.uuid1())
        self.simulate_put(path,
                          body=jsonutils.dumps({'pool_group': pool}))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data(-1, 'wee', [])
    def test_put_raises_if_invalid_capabilities(self, capabilities):
        path = self.url_prefix + '/flavors/' + str(uuid.uuid1())
        doc = {'pool_group': 'a', 'capabilities': capabilities}
        self.simulate_put(path, body=jsonutils.dumps(doc))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_put_existing_overwrites(self):
        # NOTE(cabrera): setUp creates default flavor
        expect = self.doc
        self.simulate_put(self.flavor_path,
                          body=jsonutils.dumps(expect))
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        result = self.simulate_get(self.flavor_path)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        doc = jsonutils.loads(result[0])
        self.assertEqual(expect['pool_group'], doc['pool_group'])

    def test_create_flavor_no_pool_group(self):
        self.simulate_delete(self.flavor_path)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.simulate_delete(self.pool_path)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        resp = self.simulate_put(self.flavor_path,
                                 body=jsonutils.dumps(self.doc))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        self.assertEqual(
            {'description': 'Flavor test-flavor could not be created. '
                            'Pool group mypool-group does not exist',
             'title': 'Unable to create'},
            jsonutils.loads(resp[0]))

    def test_delete_works(self):
        self.simulate_delete(self.flavor_path)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        self.simulate_get(self.flavor_path)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_get_nonexisting_raises_404(self):
        self.simulate_get(self.url_prefix + '/flavors/nonexisting')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def _flavor_expect(self, flavor, xhref, xpool):
        self.assertIn('href', flavor)
        self.assertIn('name', flavor)
        self.assertEqual(xhref, flavor['href'])
        self.assertIn('pool_group', flavor)
        self.assertEqual(xpool, flavor['pool_group'])

    def test_get_works(self):
        result = self.simulate_get(self.flavor_path)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        flavor = jsonutils.loads(result[0])
        self._flavor_expect(flavor, self.flavor_path, self.doc['pool_group'])

    def test_detailed_get_works(self):
        result = self.simulate_get(self.flavor_path,
                                   query_string='detailed=True')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        flavor = jsonutils.loads(result[0])
        self._flavor_expect(flavor, self.flavor_path, self.doc['pool_group'])
        self.assertIn('capabilities', flavor)
        self.assertEqual({}, flavor['capabilities'])

    def test_patch_raises_if_missing_fields(self):
        self.simulate_patch(self.flavor_path,
                            body=jsonutils.dumps({'location': 1}))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def _patch_test(self, doc):
        self.simulate_patch(self.flavor_path,
                            body=jsonutils.dumps(doc))
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        result = self.simulate_get(self.flavor_path,
                                   query_string='detailed=True')
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        flavor = jsonutils.loads(result[0])
        self._flavor_expect(flavor, self.flavor_path, doc['pool_group'])
        self.assertEqual(doc['capabilities'], flavor['capabilities'])

    def test_patch_works(self):
        doc = {'pool_group': 'my-pool-group', 'capabilities': {'a': 1}}
        self._patch_test(doc)

    def test_patch_works_with_extra_fields(self):
        doc = {'pool_group': 'my-pool-group', 'capabilities': {'a': 1},
               'location': 100, 'partition': 'taco'}
        self._patch_test(doc)

    @ddt.data(-1, 2**32+1, [])
    def test_patch_raises_400_on_invalid_pool_group(self, pool_group):
        self.simulate_patch(self.flavor_path,
                            body=jsonutils.dumps({'pool_group': pool_group}))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    @ddt.data(-1, 'wee', [])
    def test_patch_raises_400_on_invalid_capabilities(self, capabilities):
        doc = {'capabilities': capabilities}
        self.simulate_patch(self.flavor_path, body=jsonutils.dumps(doc))
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_patch_raises_404_if_flavor_not_found(self):
        self.simulate_patch(self.url_prefix + '/flavors/notexists',
                            body=jsonutils.dumps({'pool_group': 'test'}))
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

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

        with flavors(self, count, self.doc['pool_group']) as expected:
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
                expect = expected[i]
                path, capabilities = expect[:2]
                self._flavor_expect(s, path, self.doc['pool_group'])
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

        with flavors(self, 10, self.doc['pool_group']) as expected:
            result = self.simulate_get(self.url_prefix + '/flavors',
                                       query_string='marker=3')
            self.assertEqual(falcon.HTTP_200, self.srmock.status)
            flavor_list = jsonutils.loads(result[0])['flavors']
            self.assertEqual(6, len(flavor_list))
            path, capabilities = expected[4][:2]
            self._flavor_expect(flavor_list[0], path, self.doc['pool_group'])

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

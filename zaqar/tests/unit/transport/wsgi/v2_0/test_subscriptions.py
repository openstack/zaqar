# Copyright (c) 2015 Catalyst IT Ltd.
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

import uuid

import ddt
import falcon
from oslo.serialization import jsonutils

from zaqar import tests as testing
from zaqar.tests.unit.transport.wsgi import base


@ddt.ddt
class SubscriptionsBaseTest(base.V2Base):

    def setUp(self):
        super(SubscriptionsBaseTest, self).setUp()

        if self.conf.pooling:
            for i in range(1):
                uri = self.conf['drivers:management_store:mongodb'].uri
                doc = {'weight': 100, 'uri': uri}
                self.simulate_put(self.url_prefix + '/pools/' + str(i),
                                  body=jsonutils.dumps(doc))
                self.assertEqual(self.srmock.status, falcon.HTTP_201)
                self.addCleanup(self.simulate_delete,
                                self.url_prefix + '/pools/' + str(i),
                                headers=self.headers)

        self.project_id = '7e55e1a7exyz'
        self.headers = {
            'Client-ID': str(uuid.uuid4()),
            'X-Project-ID': self.project_id
        }
        self.queue = 'fake-topic'
        self.queue_path = self.url_prefix + '/queues/' + self.queue
        doc = '{"_ttl": 60}'
        self.simulate_put(self.queue_path, body=doc, headers=self.headers)

        self.subscription_path = (self.url_prefix + '/queues/' + self.queue +
                                  '/subscriptions')

        self.addCleanup(self._delete_subscription)

    def tearDown(self):
        super(SubscriptionsBaseTest, self).tearDown()

    def _delete_subscription(self, sid=None):
        if sid:
            self.simulate_delete(self.subscription_path + '/' + sid,
                                 headers=self.headers)
        else:
            resp = self.simulate_get(self.subscription_path,
                                     headers=self.headers)
            resp_doc = jsonutils.loads(resp[0])
            for s in resp_doc['subscriptions']:
                self.simulate_delete(self.subscription_path + '/' + s['id'],
                                     headers=self.headers)

        self.simulate_delete(self.queue_path)

    def _create_subscription(self,
                             subscriber='http://triger.me',
                             ttl=600,
                             options='{"a":1}'):
        doc = ('{"subscriber": "%s", "ttl": %s, "options": %s}' % (subscriber,
                                                                   ttl,
                                                                   options))
        return self.simulate_post(self.subscription_path, body=doc,
                                  headers=self.headers)

    def test_create_works(self):
        self._create_subscription()
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

    def test_create_duplicate_409(self):
        self._create_subscription(subscriber='http://CCC.com')
        self.assertEqual(self.srmock.status, falcon.HTTP_201)

        self._create_subscription(subscriber='http://CCC.com')
        self.assertEqual(self.srmock.status, falcon.HTTP_409)

    def test_create_invalid_body_400(self):
        resp = self._create_subscription(options='xxx')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('body could not be parsed', resp_doc['description'])

    def test_create_invalid_subscriber_400(self):
        resp = self._create_subscription(subscriber='fake')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('must be supported in the list', resp_doc['description'])

    def test_create_unsupported_subscriber_400(self):
        resp = self._create_subscription(subscriber='email://fake')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('must be supported in the list',
                      resp_doc['description'])

    def test_create_invalid_options_400(self):
        resp = self._create_subscription(options='1')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('must be a dict', resp_doc['description'])

    def test_create_invalid_ttl(self):
        resp = self._create_subscription(ttl='"invalid"')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('must be an integer', resp_doc['description'])

    def _list_subscription(self, count=10, limit=10, marker=None):
        for i in range(count):
            self._create_subscription(subscriber='http://' + str(i))

        query = '?limit={0}'.format(limit)
        if marker:
            query += '&marker={1}'.format(marker)

        resp = self.simulate_get(self.subscription_path,
                                 query_string=query,
                                 headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        resp_doc = jsonutils.loads(resp[0])
        self.assertIsInstance(resp_doc, dict)
        self.assertIn('subscriptions', resp_doc)
        self.assertIn('links', resp_doc)
        subscriptions_list = resp_doc['subscriptions']

        link = resp_doc['links'][0]
        self.assertEqual('next', link['rel'])
        href = falcon.uri.parse_query_string(link['href'])
        self.assertIn('marker', href)
        self.assertEqual(href['limit'], str(limit))

        next_query_string = ('?marker={marker}&limit={limit}').format(**href)
        next_result = self.simulate_get(link['href'].split('?')[0],
                                        query_string=next_query_string)
        next_subscriptions = jsonutils.loads(next_result[0])
        next_subscriptions_list = next_subscriptions['subscriptions']

        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        self.assertIn('links', next_subscriptions)
        if limit < count:
            self.assertEqual(len(next_subscriptions_list),
                             min(limit, count-limit))
        else:
            self.assertTrue(len(next_subscriptions_list) == 0)

        self.assertEqual(len(subscriptions_list), min(limit, count))

    def test_list_works(self):
        self._list_subscription()

    @ddt.data(1, 5, 10, 15)
    def test_listing_works_with_limit(self, limit):
        self._list_subscription(count=15, limit=limit)

    def test_listing_marker_is_respected(self):
        for i in range(15):
            self._create_subscription(subscriber='http://' + str(i))

        resp = self.simulate_get(self.subscription_path,
                                 query_string='?limit=20',
                                 headers=self.headers)
        subscriptions_list = jsonutils.loads(resp[0])['subscriptions']
        id_list = sorted([s['id'] for s in subscriptions_list])

        resp = self.simulate_get(self.subscription_path,
                                 query_string='?marker={0}'.format(id_list[9]),
                                 headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        next_subscriptions_list = jsonutils.loads(resp[0])['subscriptions']
        self.assertEqual(len(next_subscriptions_list), 5)
        self.assertEqual(subscriptions_list[10], next_subscriptions_list[0])

    def test_get_works(self):
        self._create_subscription()
        resp = self.simulate_get(self.subscription_path,
                                 headers=self.headers)
        resp_doc = jsonutils.loads(resp[0])
        sid = resp_doc['subscriptions'][0]['id']
        subscriber = resp_doc['subscriptions'][0]['subscriber']

        resp = self.simulate_get(self.subscription_path + '/' + sid,
                                 headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        resp_doc = jsonutils.loads(resp[0])
        self.assertEqual(sid, resp_doc['id'])
        self.assertEqual(subscriber, resp_doc['subscriber'])

    def test_get_nonexisting_raise_404(self):
        self.simulate_get(self.subscription_path + '/fake',
                          headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_patch_works(self):
        self._create_subscription()
        resp = self.simulate_get(self.subscription_path,
                                 headers=self.headers)
        resp_doc = jsonutils.loads(resp[0])
        sid = resp_doc['subscriptions'][0]['id']

        resp = self.simulate_patch(self.subscription_path + '/' + sid,
                                   body='{"ttl": 300}',
                                   headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        resp = self.simulate_get(self.subscription_path + '/' + sid,
                                 headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        resp_doc = jsonutils.loads(resp[0])
        self.assertEqual(resp_doc['ttl'], 300)

    def test_patch_nonexisting_raise_404(self):
        self.simulate_patch(self.subscription_path + '/x',
                            body='{"ttl": 300}',
                            headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)

    def test_patch_invalid_ttl(self):
        self.simulate_patch(self.subscription_path + '/x',
                            body='{"ttl": "invalid"}',
                            headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

    def test_delete_works(self):
        self._create_subscription()
        resp = self.simulate_get(self.subscription_path,
                                 headers=self.headers)
        resp_doc = jsonutils.loads(resp[0])
        sid = resp_doc['subscriptions'][0]['id']

        resp = self.simulate_get(self.subscription_path + '/' + sid,
                                 headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        self.simulate_delete(self.subscription_path + '/' + sid,
                             headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_204)

        resp = self.simulate_get(self.subscription_path + '/' + sid,
                                 headers=self.headers)
        self.assertEqual(self.srmock.status, falcon.HTTP_404)


class TestSubscriptionsMongoDB(SubscriptionsBaseTest):

    config_file = 'wsgi_mongodb_pooled.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestSubscriptionsMongoDB, self).setUp()

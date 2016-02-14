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
import mock
from oslo_serialization import jsonutils

from zaqar.storage import errors as storage_errors
from zaqar import tests as testing
from zaqar.tests.unit.transport.wsgi import base


@ddt.ddt
class TestSubscriptionsMongoDB(base.V2Base):

    config_file = 'wsgi_mongodb_pooled.conf'

    @testing.requires_mongodb
    def setUp(self):
        super(TestSubscriptionsMongoDB, self).setUp()

        if self.conf.pooling:
            for i in range(1):
                uri = self.conf['drivers:management_store:mongodb'].uri
                doc = {'weight': 100, 'uri': uri}
                self.simulate_put(self.url_prefix + '/pools/' + str(i),
                                  body=jsonutils.dumps(doc))
                self.assertEqual(falcon.HTTP_201, self.srmock.status)
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

    def tearDown(self):
        resp = self.simulate_get(self.subscription_path,
                                 headers=self.headers)
        resp_doc = jsonutils.loads(resp[0])
        for s in resp_doc['subscriptions']:
            self.simulate_delete(self.subscription_path + '/' + s['id'],
                                 headers=self.headers)

        self.simulate_delete(self.queue_path)
        super(TestSubscriptionsMongoDB, self).tearDown()

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
        resp = self._create_subscription()
        self.assertEqual(falcon.HTTP_201, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])

        resp_list = self.simulate_get(self.subscription_path,
                                      headers=self.headers)
        resp_list_doc = jsonutils.loads(resp_list[0])
        sid = resp_list_doc['subscriptions'][0]['id']

        self.assertEqual(resp_doc['subscription_id'], sid)

    def test_create_duplicate_409(self):
        self._create_subscription(subscriber='http://CCC.com')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self._create_subscription(subscriber='http://CCC.com')
        self.assertEqual(falcon.HTTP_409, self.srmock.status)

    def test_create_invalid_body_400(self):
        resp = self._create_subscription(options='xxx')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('body could not be parsed', resp_doc['description'])

    def test_create_no_body(self):
        resp = self.simulate_post(self.subscription_path, headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        self.assertIn('Missing parameter',
                      jsonutils.loads(resp[0])['description'])

    def test_create_invalid_subscriber_400(self):
        resp = self._create_subscription(subscriber='fake')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('must be supported in the list', resp_doc['description'])

    def test_create_unsupported_subscriber_400(self):
        resp = self._create_subscription(subscriber='email://fake')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('must be supported in the list',
                      resp_doc['description'])

    def test_create_invalid_options_400(self):
        resp = self._create_subscription(options='1')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('must be a dict', resp_doc['description'])

    def test_create_invalid_ttl(self):
        resp = self._create_subscription(ttl='"invalid"')
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('must be an integer', resp_doc['description'])

    def _list_subscription(self, count=10, limit=10, marker=None):
        for i in range(count):
            self._create_subscription(subscriber='http://' + str(i))

        query = 'limit={0}'.format(limit)
        if marker:
            query += '&marker={1}'.format(marker)

        resp = self.simulate_get(self.subscription_path,
                                 query_string=query,
                                 headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        resp_doc = jsonutils.loads(resp[0])
        self.assertIsInstance(resp_doc, dict)
        self.assertIn('subscriptions', resp_doc)
        self.assertIn('links', resp_doc)
        subscriptions_list = resp_doc['subscriptions']

        link = resp_doc['links'][0]
        self.assertEqual('next', link['rel'])
        href = falcon.uri.parse_query_string(link['href'].split('?')[1])
        self.assertIn('marker', href)
        self.assertEqual(str(limit), href['limit'])

        next_query_string = ('marker={marker}&limit={limit}').format(**href)
        next_result = self.simulate_get(link['href'].split('?')[0],
                                        query_string=next_query_string)
        next_subscriptions = jsonutils.loads(next_result[0])
        next_subscriptions_list = next_subscriptions['subscriptions']

        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        self.assertIn('links', next_subscriptions)
        if limit < count:
            self.assertEqual(min(limit, count-limit),
                             len(next_subscriptions_list))
        else:
            self.assertTrue(len(next_subscriptions_list) == 0)

        self.assertEqual(min(limit, count), len(subscriptions_list))

    def test_list_works(self):
        self._list_subscription()

    def test_list_returns_503_on_nopoolfound_exception(self):
        arbitrary_number = 644079696574693
        project_id = str(arbitrary_number)
        client_id = str(uuid.uuid4())
        header = {
            'X-Project-ID': project_id,
            'Client-ID': client_id
        }

        subscription_controller = self.boot.storage.subscription_controller

        with mock.patch.object(subscription_controller, 'list') as \
                mock_subscription_list:

            def subscription_generator():
                raise storage_errors.NoPoolFound()

            # This generator tries to be like subscription controller list
            # generator in some ways.
            def fake_generator():
                yield subscription_generator()
                yield {}
            mock_subscription_list.return_value = fake_generator()
            self.simulate_get(self.subscription_path, headers=header)
            self.assertEqual(falcon.HTTP_503, self.srmock.status)

    def test_list_empty(self):
        resp = self.simulate_get(self.subscription_path,
                                 headers=self.headers)

        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        resp_doc = jsonutils.loads(resp[0])
        self.assertIsInstance(resp_doc, dict)
        self.assertIn('subscriptions', resp_doc)
        self.assertIn('links', resp_doc)
        self.assertEqual([], resp_doc['subscriptions'])
        self.assertEqual([], resp_doc['links'])

    @ddt.data(1, 5, 10, 15)
    def test_listing_works_with_limit(self, limit):
        self._list_subscription(count=15, limit=limit)

    def test_listing_marker_is_respected(self):
        for i in range(15):
            self._create_subscription(subscriber='http://' + str(i))

        resp = self.simulate_get(self.subscription_path,
                                 query_string='limit=20',
                                 headers=self.headers)
        subscriptions_list = jsonutils.loads(resp[0])['subscriptions']
        id_list = sorted([s['id'] for s in subscriptions_list])

        resp = self.simulate_get(self.subscription_path,
                                 query_string='marker={0}'.format(id_list[9]),
                                 headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        next_subscriptions_list = jsonutils.loads(resp[0])['subscriptions']
        self.assertEqual(5, len(next_subscriptions_list))
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
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])
        self.assertEqual(sid, resp_doc['id'])
        self.assertEqual(subscriber, resp_doc['subscriber'])

    def test_get_nonexisting_raise_404(self):
        self.simulate_get(self.subscription_path + '/fake',
                          headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_patch_works(self):
        self._create_subscription()
        resp = self.simulate_get(self.subscription_path,
                                 headers=self.headers)
        resp_doc = jsonutils.loads(resp[0])
        sid = resp_doc['subscriptions'][0]['id']

        resp = self.simulate_patch(self.subscription_path + '/' + sid,
                                   body='{"ttl": 300}',
                                   headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        resp = self.simulate_get(self.subscription_path + '/' + sid,
                                 headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])
        self.assertEqual(300, resp_doc['ttl'])

    def test_patch_nonexisting_raise_404(self):
        self.simulate_patch(self.subscription_path + '/x',
                            body='{"ttl": 300}',
                            headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

    def test_patch_to_duplicate_raise_409(self):
        self._create_subscription()
        toupdate = self._create_subscription(subscriber='http://update.me',
                                             ttl=600,
                                             options='{"a":1}')
        toupdate_sid = jsonutils.loads(toupdate[0])['subscription_id']
        doc = {'subscriber': 'http://triger.me'}
        self.simulate_patch(self.subscription_path + '/' + toupdate_sid,
                            body=jsonutils.dumps(doc),
                            headers=self.headers)
        self.assertEqual(falcon.HTTP_409, self.srmock.status)

    def test_patch_no_body(self):
        self._create_subscription()
        resp = self.simulate_get(self.subscription_path,
                                 headers=self.headers)
        resp_doc = jsonutils.loads(resp[0])
        sid = resp_doc['subscriptions'][0]['id']

        resp = self.simulate_patch(self.subscription_path + '/' + sid,
                                   headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

        resp_doc = jsonutils.loads(resp[0])
        self.assertNotIn('{subscription_id}', resp_doc['description'])

    def test_patch_invalid_ttl(self):
        self.simulate_patch(self.subscription_path + '/x',
                            body='{"ttl": "invalid"}',
                            headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

    def test_delete_works(self):
        self._create_subscription()
        resp = self.simulate_get(self.subscription_path,
                                 headers=self.headers)
        resp_doc = jsonutils.loads(resp[0])
        sid = resp_doc['subscriptions'][0]['id']

        resp = self.simulate_get(self.subscription_path + '/' + sid,
                                 headers=self.headers)
        self.assertEqual(falcon.HTTP_200, self.srmock.status)

        self.simulate_delete(self.subscription_path + '/' + sid,
                             headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

        resp = self.simulate_get(self.subscription_path + '/' + sid,
                                 headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

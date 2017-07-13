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


import ddt
import falcon
import mock
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from zaqar.common import auth
from zaqar.notification import notifier
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
            'Client-ID': uuidutils.generate_uuid(),
            'X-Project-ID': self.project_id
        }
        self.queue = 'fake-topic'
        self.queue_path = self.url_prefix + '/queues/' + self.queue
        doc = '{"_ttl": 60}'
        self.simulate_put(self.queue_path, body=doc, headers=self.headers)

        self.subscription_path = (self.url_prefix + '/queues/' + self.queue +
                                  '/subscriptions')
        self.subscription = 'fake-id'
        self.confirm_path = (self.url_prefix + '/queues/' + self.queue +
                             '/subscriptions/' + self.subscription +
                             '/confirm')
        self.conf.signed_url.secret_key = 'test_key'

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

        # the subscription is not confirmed, So the second request will
        # retry confirm and return 201 again.
        self._create_subscription(subscriber='http://CCC.com')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

    @mock.patch.object(notifier.NotifierDriver, 'send_confirm_notification')
    def test_create_and_send_notification(self, mock_send_confirm):
        self._create_subscription(subscriber='http://CCC.com')
        self.assertEqual(1, mock_send_confirm.call_count)

    @mock.patch.object(notifier.NotifierDriver, 'send_confirm_notification')
    def test_recreate(self, mock_send_confirm):
        resp = self._create_subscription(subscriber='http://CCC.com')
        resp_doc = jsonutils.loads(resp[0])
        s_id1 = resp_doc['subscription_id']
        self.assertEqual(1, mock_send_confirm.call_count)

        resp = self._create_subscription(subscriber='http://CCC.com')
        resp_doc = jsonutils.loads(resp[0])
        s_id2 = resp_doc['subscription_id']
        self.assertEqual(2, mock_send_confirm.call_count)

        self.assertEqual(s_id1, s_id2)

    @mock.patch.object(notifier.NotifierDriver, 'send_confirm_notification')
    def test_recreate_after_confirmed(self, mock_send_confirm):
        resp = self._create_subscription(subscriber='http://CCC.com')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        doc = '{"confirmed": true}'
        resp_doc = jsonutils.loads(resp[0])
        confirm_path = (self.url_prefix + '/queues/' + self.queue +
                        '/subscriptions/' + resp_doc['subscription_id'] +
                        '/confirm')
        self.simulate_put(confirm_path, body=doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)
        self.assertEqual(1, mock_send_confirm.call_count)

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
            self.assertEqual(0, len(next_subscriptions_list))

        self.assertEqual(min(limit, count), len(subscriptions_list))

    def test_list_works(self):
        self._list_subscription()

    def test_list_returns_503_on_nopoolfound_exception(self):
        arbitrary_number = 644079696574693
        project_id = str(arbitrary_number)
        client_id = uuidutils.generate_uuid()
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
        # The subscriptions's age should be 0 at this moment. But in some
        # unexpected case, such as slow test, the age maybe larger than 0.
        self.assertGreaterEqual(next_subscriptions_list[0].pop('age'),
                                subscriptions_list[10].pop('age'))
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

    def test_patch_invalid_body(self):
        resp = self.simulate_patch(self.subscription_path + '/x',
                                   body='[1]',
                                   headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])
        self.assertEqual('Subscriptions must be a dict.',
                         resp_doc['description'])

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

    @mock.patch.object(auth, 'create_trust_id')
    def test_create_with_trust(self, create_trust):
        create_trust.return_value = 'trust_id'
        self.headers['X-USER-ID'] = 'user-id'
        self.headers['X-ROLES'] = 'my-roles'
        self._create_subscription('trust+http://example.com')
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        self.assertEqual('user-id', create_trust.call_args[0][1])
        self.assertEqual(self.project_id, create_trust.call_args[0][2])
        self.assertEqual(['my-roles'], create_trust.call_args[0][3])

        resp_list = self.simulate_get(self.subscription_path,
                                      headers=self.headers)
        resp_list_doc = jsonutils.loads(resp_list[0])
        options = resp_list_doc['subscriptions'][0]['options']

        self.assertEqual({'a': 1, 'trust_id': 'trust_id'}, options)

    def test_confirm(self):
        doc = '{"confirmed": true}'
        resp = self._create_subscription()
        resp_doc = jsonutils.loads(resp[0])
        confirm_path = (self.url_prefix + '/queues/' + self.queue +
                        '/subscriptions/' + resp_doc['subscription_id'] +
                        '/confirm')
        self.simulate_put(confirm_path, body=doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_204, self.srmock.status)

    def test_confirm_with_invalid_body(self):
        doc = '{confirmed:123}'
        resp = self.simulate_put(self.confirm_path, body=doc,
                                 headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])
        self.assertIn('body could not be parsed', resp_doc['description'])

    def test_confirm_without_boolean_body(self):
        doc = '{"confirmed":123}'
        resp = self.simulate_put(self.confirm_path, body=doc,
                                 headers=self.headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)
        resp_doc = jsonutils.loads(resp[0])
        self.assertEqual("The 'confirmed' should be boolean.",
                         resp_doc['description'])

    def test_confirm_with_non_subscription(self):
        doc = '{"confirmed": true}'
        self.simulate_put(self.confirm_path, body=doc, headers=self.headers)
        self.assertEqual(falcon.HTTP_404, self.srmock.status)

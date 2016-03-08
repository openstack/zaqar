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

from __future__ import division

import time
import uuid

import ddt

from zaqar.tests.functional import base
from zaqar.tests.functional import helpers as func_helpers
from zaqar.tests import helpers


@ddt.ddt
class TestSubscriptions(base.V2FunctionalTestBase):

    """Tests for Subscriptions."""

    server_class = base.ZaqarServer

    def setUp(self):
        super(TestSubscriptions, self).setUp()

        self.queue_name = uuid.uuid1()
        self.queue_url = ("{url}/{version}/queues/{queue}".format(
                          url=self.cfg.zaqar.url,
                          version="v2",
                          queue=self.queue_name))

        self.client.put(self.queue_url)

        self.subscriptions_url = self.queue_url + '/subscriptions/'
        self.client.set_base_url(self.subscriptions_url)

    def tearDown(self):
        # Delete test queue subscriptions after each test case.
        result = self.client.get(self.subscriptions_url)
        subscriptions = result.json()['subscriptions']
        for sub in subscriptions:
            sub_url = self.subscriptions_url + sub['id']
            self.client.delete(sub_url)
        # Delete test queue.
        self.client.delete(self.queue_url)
        super(TestSubscriptions, self).tearDown()

    @helpers.is_slow(condition=lambda self: self.class_ttl_gc_interval > 1)
    def test_expired_subscription(self):
        # Default TTL value is 600.
        doc = func_helpers.create_subscription_body()
        result = self.client.post(data=doc)
        self.assertEqual(201, result.status_code)
        longlive_id = result.json()['subscription_id']

        # This is a minimum TTL allowed by server.
        ttl_for_shortlive = 60
        doc = func_helpers.create_subscription_body(
            subscriber='http://expire.me', ttl=ttl_for_shortlive)
        result = self.client.post(data=doc)
        self.assertEqual(201, result.status_code)
        shortlive_id = result.json()['subscription_id']
        shortlive_url = self.subscriptions_url + shortlive_id

        # Let's wait for subscription to expire.
        for i in range(self.class_ttl_gc_interval + ttl_for_shortlive):
            time.sleep(1)
            result = self.client.get(shortlive_url)
            if result.status_code == 404:
                break
        else:
            self.fail("Didn't remove the subscription in time.")

        # Make sure the expired subscription is not returned when listing.
        result = self.client.get(self.subscriptions_url)
        self.assertEqual(200, result.status_code)
        subscriptions = result.json()['subscriptions']
        self.assertEqual(1, len(subscriptions))
        self.assertEqual(longlive_id, subscriptions[0]['id'])

    @helpers.is_slow(condition=lambda self: self.class_ttl_gc_interval > 1)
    def test_update_ttl(self):
        # Default TTL value is 600.
        doc = func_helpers.create_subscription_body()
        result = self.client.post(data=doc)
        self.assertEqual(201, result.status_code)
        subscription_id = result.json()['subscription_id']
        subscription_url = self.subscriptions_url + subscription_id

        # This is a minimum TTL allowed by server.
        updated_ttl = 60
        update_fields = {
            'ttl': updated_ttl
        }
        result = self.client.patch(subscription_url, data=update_fields)
        self.assertEqual(204, result.status_code)

        # Let's wait for updated subscription to expire.
        for i in range(self.class_ttl_gc_interval + updated_ttl):
            time.sleep(1)
            result = self.client.get(subscription_url)
            if result.status_code == 404:
                break
        else:
            self.fail("Didn't remove the subscription in time.")

        # Make sure the expired subscription is not returned when listing.
        result = self.client.get(self.subscriptions_url)
        self.assertEqual(200, result.status_code)
        subscriptions = result.json()['subscriptions']
        self.assertEqual(0, len(subscriptions))

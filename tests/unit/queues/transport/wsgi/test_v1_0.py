# Copyright (c) 2014 Rackspace, Inc.
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

import falcon

from zaqar.tests.queues.transport.wsgi import base
from zaqar.tests.queues.transport.wsgi import v1


# --------------------------------------------------------------------------
# Identical or just minor variations across versions
# --------------------------------------------------------------------------

URL_PREFIX = '/v1'


class TestAuth(v1.TestAuth):
    url_prefix = URL_PREFIX


class TestClaimsFaultyDriver(v1.TestClaimsFaultyDriver):
    url_prefix = URL_PREFIX


class TestClaimsMongoDB(v1.TestClaimsMongoDB):
    url_prefix = URL_PREFIX


class TestClaimsSqlalchemy(v1.TestClaimsSqlalchemy):
    url_prefix = URL_PREFIX


class TestDefaultLimits(v1.TestDefaultLimits):
    url_prefix = URL_PREFIX


class TestHomeDocument(v1.TestHomeDocument):
    url_prefix = URL_PREFIX


class TestMediaType(v1.TestMediaType):
    url_prefix = URL_PREFIX


class TestMessagesFaultyDriver(v1.TestMessagesFaultyDriver):
    url_prefix = URL_PREFIX


class TestMessagesMongoDB(v1.TestMessagesMongoDB):
    url_prefix = URL_PREFIX


class TestMessagesMongoDBPooled(v1.TestMessagesMongoDBPooled):
    url_prefix = URL_PREFIX


class TestMessagesSqlalchemy(v1.TestMessagesSqlalchemy):
    url_prefix = URL_PREFIX


class TestQueueFaultyDriver(v1.TestQueueFaultyDriver):
    url_prefix = URL_PREFIX


class TestQueueLifecycleMongoDB(v1.TestQueueLifecycleMongoDB):
    url_prefix = URL_PREFIX


class TestQueueLifecycleSqlalchemy(v1.TestQueueLifecycleSqlalchemy):
    url_prefix = URL_PREFIX


class TestPoolsMongoDB(v1.TestPoolsMongoDB):
    url_prefix = URL_PREFIX


class TestPoolsSqlalchemy(v1.TestPoolsSqlalchemy):
    url_prefix = URL_PREFIX


class TestValidation(v1.TestValidation):
    url_prefix = URL_PREFIX


# --------------------------------------------------------------------------
# v1.0 only
# --------------------------------------------------------------------------

class TestHealth(base.V1Base):

    config_file = 'wsgi_sqlalchemy.conf'

    def test_get(self):
        response = self.simulate_get('/v1/health')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

    def test_head(self):
        response = self.simulate_head('/v1/health')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

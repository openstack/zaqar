# Copyright (c) 2014 Rackspace, Inc.
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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import falcon

from marconi.tests.queues.transport import wsgi


#----------------------------------------------------------------------------
# Identical or just minor variations across versions
#----------------------------------------------------------------------------

URL_PREFIX = '/v1'


class TestAuth(wsgi.TestAuth):
    url_prefix = URL_PREFIX


class TestClaimsFaultyDriver(wsgi.TestClaimsFaultyDriver):
    url_prefix = URL_PREFIX


class TestClaimsMongoDB(wsgi.TestClaimsMongoDB):
    url_prefix = URL_PREFIX


class TestClaimsSQLite(wsgi.TestClaimsSQLite):
    url_prefix = URL_PREFIX


class TestDefaultLimits(wsgi.TestDefaultLimits):
    url_prefix = URL_PREFIX


class TestHomeDocument(wsgi.TestHomeDocument):
    url_prefix = URL_PREFIX


class TestMediaType(wsgi.TestMediaType):
    url_prefix = URL_PREFIX


class TestMessagesFaultyDriver(wsgi.TestMessagesFaultyDriver):
    url_prefix = URL_PREFIX


class TestMessagesMongoDB(wsgi.TestMessagesMongoDB):
    url_prefix = URL_PREFIX


class TestMessagesMongoDBSharded(wsgi.TestMessagesMongoDBSharded):
    url_prefix = URL_PREFIX


class TestMessagesSQLite(wsgi.TestMessagesSQLite):
    url_prefix = URL_PREFIX


class TestQueueFaultyDriver(wsgi.TestQueueFaultyDriver):
    url_prefix = URL_PREFIX


class TestQueueLifecycleMongoDB(wsgi.TestQueueLifecycleMongoDB):
    url_prefix = URL_PREFIX


class TestQueueLifecycleSQLite(wsgi.TestQueueLifecycleSQLite):
    url_prefix = URL_PREFIX


class TestShardsMongoDB(wsgi.TestShardsMongoDB):
    url_prefix = URL_PREFIX


#----------------------------------------------------------------------------
# v1.0 only
#----------------------------------------------------------------------------

class TestHealth(wsgi.TestBase):

    config_file = 'wsgi_sqlalchemy.conf'

    def test_get(self):
        response = self.simulate_get('/v1/health')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

    def test_head(self):
        response = self.simulate_head('/v1/health')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

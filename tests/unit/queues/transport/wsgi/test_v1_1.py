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

from marconi.tests.queues.transport.wsgi import base
from marconi.tests.queues.transport.wsgi import v1_1

#----------------------------------------------------------------------------
# Identical or just minor variations across versions
#----------------------------------------------------------------------------

URL_PREFIX = '/v1.1'


class TestAuth(v1_1.TestAuth):
    url_prefix = URL_PREFIX


class TestClaimsFaultyDriver(v1_1.TestClaimsFaultyDriver):
    url_prefix = URL_PREFIX


class TestClaimsMongoDB(v1_1.TestClaimsMongoDB):
    url_prefix = URL_PREFIX


class TestClaimsSqlalchemy(v1_1.TestClaimsSqlalchemy):
    url_prefix = URL_PREFIX


class TestDefaultLimits(v1_1.TestDefaultLimits):
    url_prefix = URL_PREFIX


class TestHomeDocument(v1_1.TestHomeDocument):
    url_prefix = URL_PREFIX


class TestMediaType(v1_1.TestMediaType):
    url_prefix = URL_PREFIX


class TestMessagesFaultyDriver(v1_1.TestMessagesFaultyDriver):
    url_prefix = URL_PREFIX


class TestMessagesMongoDB(v1_1.TestMessagesMongoDB):
    url_prefix = URL_PREFIX


class TestMessagesMongoDBSharded(v1_1.TestMessagesMongoDBSharded):
    url_prefix = URL_PREFIX


class TestMessagesSqlalchemy(v1_1.TestMessagesSqlalchemy):
    url_prefix = URL_PREFIX


class TestQueueFaultyDriver(v1_1.TestQueueFaultyDriver):
    url_prefix = URL_PREFIX


# TODO(kgriffs): Having to list a separate test for each backend is
# sort of a pain; is there a better way?
class TestQueueLifecycleMongoDB(v1_1.TestQueueLifecycleMongoDB):
    url_prefix = URL_PREFIX


class TestQueueLifecycleSqlalchemy(v1_1.TestQueueLifecycleSqlalchemy):
    url_prefix = URL_PREFIX


class TestShardsMongoDB(v1_1.TestShardsMongoDB):
    url_prefix = URL_PREFIX


class TestShardsSqlalchemy(v1_1.TestShardsSqlalchemy):
    url_prefix = URL_PREFIX


#----------------------------------------------------------------------------
# v1.1 only
#----------------------------------------------------------------------------

class TestPing(base.V1_1Base):

    config_file = 'wsgi_sqlalchemy.conf'

    def test_get(self):
        # TODO(kgriffs): Make use of setUp for setting the URL prefix
        # so we can just say something like:
        #
        #     response = self.simulate_get('/ping')
        #
        response = self.simulate_get('/v1.1/ping')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

    def test_head(self):
        response = self.simulate_head('/v1.1/ping')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])


class TestHealth(base.V1_1Base):

    config_file = 'wsgi_sqlalchemy.conf'

    def test_get(self):
        response = self.simulate_get('/v1.1/health')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

    def test_head(self):
        response = self.simulate_head('/v1.1/health')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

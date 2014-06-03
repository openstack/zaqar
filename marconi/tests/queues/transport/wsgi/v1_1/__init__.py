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

from marconi.tests.queues.transport.wsgi.v1_1 import test_auth
from marconi.tests.queues.transport.wsgi.v1_1 import test_claims
from marconi.tests.queues.transport.wsgi.v1_1 import test_default_limits
from marconi.tests.queues.transport.wsgi.v1_1 import test_home
from marconi.tests.queues.transport.wsgi.v1_1 import test_media_type
from marconi.tests.queues.transport.wsgi.v1_1 import test_messages
from marconi.tests.queues.transport.wsgi.v1_1 import test_queue_lifecycle as lc
from marconi.tests.queues.transport.wsgi.v1_1 import test_shards

TestAuth = test_auth.TestAuth
TestClaimsFaultyDriver = test_claims.TestClaimsFaultyDriver
TestClaimsMongoDB = test_claims.TestClaimsMongoDB
TestClaimsSqlalchemy = test_claims.TestClaimsSqlalchemy
TestDefaultLimits = test_default_limits.TestDefaultLimits
TestHomeDocument = test_home.TestHomeDocument
TestMediaType = test_media_type.TestMediaType
TestMessagesFaultyDriver = test_messages.TestMessagesFaultyDriver
TestMessagesMongoDB = test_messages.TestMessagesMongoDB
TestMessagesMongoDBSharded = test_messages.TestMessagesMongoDBSharded
TestMessagesSqlalchemy = test_messages.TestMessagesSqlalchemy
TestQueueFaultyDriver = lc.TestQueueLifecycleFaultyDriver
TestQueueLifecycleMongoDB = lc.TestQueueLifecycleMongoDB
TestQueueLifecycleSqlalchemy = lc.TestQueueLifecycleSqlalchemy
TestShardsMongoDB = test_shards.TestShardsMongoDB
TestShardsSqlalchemy = test_shards.TestShardsSqlalchemy

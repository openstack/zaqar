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

from zaqar.tests.queues.transport.wsgi.v1_1 import test_auth
from zaqar.tests.queues.transport.wsgi.v1_1 import test_claims
from zaqar.tests.queues.transport.wsgi.v1_1 import test_default_limits
from zaqar.tests.queues.transport.wsgi.v1_1 import test_home
from zaqar.tests.queues.transport.wsgi.v1_1 import test_media_type
from zaqar.tests.queues.transport.wsgi.v1_1 import test_messages
from zaqar.tests.queues.transport.wsgi.v1_1 import test_pools
from zaqar.tests.queues.transport.wsgi.v1_1 import test_queue_lifecycle as l
from zaqar.tests.queues.transport.wsgi.v1_1 import test_validation

TestAuth = test_auth.TestAuth
TestClaimsFaultyDriver = test_claims.TestClaimsFaultyDriver
TestClaimsMongoDB = test_claims.TestClaimsMongoDB
TestClaimsSqlalchemy = test_claims.TestClaimsSqlalchemy
TestDefaultLimits = test_default_limits.TestDefaultLimits
TestHomeDocument = test_home.TestHomeDocument
TestMediaType = test_media_type.TestMediaType
TestMessagesFaultyDriver = test_messages.TestMessagesFaultyDriver
TestMessagesMongoDB = test_messages.TestMessagesMongoDB
TestMessagesMongoDBPooled = test_messages.TestMessagesMongoDBPooled
TestMessagesSqlalchemy = test_messages.TestMessagesSqlalchemy
TestQueueFaultyDriver = l.TestQueueLifecycleFaultyDriver
TestQueueLifecycleMongoDB = l.TestQueueLifecycleMongoDB
TestQueueLifecycleSqlalchemy = l.TestQueueLifecycleSqlalchemy
TestPoolsMongoDB = test_pools.TestPoolsMongoDB
TestPoolsSqlalchemy = test_pools.TestPoolsSqlalchemy
TestValidation = test_validation.TestValidation

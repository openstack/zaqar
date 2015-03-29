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

from zaqar.tests.unit.transport.wsgi.v2_0 import test_auth
from zaqar.tests.unit.transport.wsgi.v2_0 import test_claims
from zaqar.tests.unit.transport.wsgi.v2_0 import test_default_limits
from zaqar.tests.unit.transport.wsgi.v2_0 import test_flavors
from zaqar.tests.unit.transport.wsgi.v2_0 import test_health
from zaqar.tests.unit.transport.wsgi.v2_0 import test_home
from zaqar.tests.unit.transport.wsgi.v2_0 import test_media_type
from zaqar.tests.unit.transport.wsgi.v2_0 import test_messages
from zaqar.tests.unit.transport.wsgi.v2_0 import test_pools
from zaqar.tests.unit.transport.wsgi.v2_0 import test_queue_lifecycle as l
from zaqar.tests.unit.transport.wsgi.v2_0 import test_validation

TestAuth = test_auth.TestAuth
TestClaimsFaultyDriver = test_claims.TestClaimsFaultyDriver
TestClaimsMongoDB = test_claims.TestClaimsMongoDB
TestDefaultLimits = test_default_limits.TestDefaultLimits
TestHealthMongoDB = test_health.TestHealthMongoDB
TestHealthFaultyDriver = test_health.TestHealthFaultyDriver
TestHomeDocument = test_home.TestHomeDocument
TestMediaType = test_media_type.TestMediaType
TestMessagesFaultyDriver = test_messages.TestMessagesFaultyDriver
TestMessagesMongoDB = test_messages.TestMessagesMongoDB
TestMessagesMongoDBPooled = test_messages.TestMessagesMongoDBPooled
TestQueueFaultyDriver = l.TestQueueLifecycleFaultyDriver
TestQueueLifecycleMongoDB = l.TestQueueLifecycleMongoDB
TestQueueLifecycleSqlalchemy = l.TestQueueLifecycleSqlalchemy
TestPoolsMongoDB = test_pools.TestPoolsMongoDB
TestPoolsSqlalchemy = test_pools.TestPoolsSqlalchemy
TestValidation = test_validation.TestValidation
TestFlavorsMongoDB = test_flavors.TestFlavorsMongoDB

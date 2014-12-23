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

# TODO(kgriffs): Consider consolidating all of these tests into a
# single module.

from zaqar.tests.unit.transport.wsgi import base

TestBase = base.TestBase
TestBaseFaulty = base.TestBaseFaulty
V1Base = base.V1Base
V1_1Base = base.V1_1Base

# Copyright (c) 2015 Catalyst IT Ltd.
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

from collections import namedtuple

from oslo_policy import policy

from zaqar import context
from zaqar.tests import base
from zaqar.transport import acl
from zaqar.transport.wsgi import errors


class TestAcl(base.TestBase):

    def setUp(self):
        super(TestAcl, self).setUp()
        ctx = context.RequestContext()
        request_class = namedtuple("Request", ("env",))
        self.request = request_class({"zaqar.context": ctx})

    def _set_policy(self, json):
        acl.setup_policy(self.conf)
        rules = policy.Rules.load_json(json)
        acl.ENFORCER.set_rules(rules, use_conf=False)

    def test_policy_allow(self):
        @acl.enforce("queues:get_all")
        def test(ign, request):
            pass

        json = '{"queues:get_all": ""}'
        self._set_policy(json)

        test(None, self.request)

    def test_policy_deny(self):
        @acl.enforce("queues:get_all")
        def test(ign, request):
            pass

        json = '{"queues:get_all": "!"}'
        self._set_policy(json)

        self.assertRaises(errors.HTTPForbidden, test, None, self.request)

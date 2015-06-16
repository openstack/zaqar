# Copyright (c) 2013 Rackspace, Inc.
# Copyright (c) 2013 Red Hat, Inc.
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


from zaqar.common.api import request
from zaqar.tests import base


class TestRequest(base.TestBase):

    def test_request_deserialized(self):
        action = 'message_post'
        data = '{"data": "tons of GBs"}'
        req = request.Request(action=action, body=data)
        self.assertIsInstance(req.deserialized_content, dict)

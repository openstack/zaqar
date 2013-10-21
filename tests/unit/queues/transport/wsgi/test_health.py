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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import falcon

import base  # noqa


class TestHealth(base.TestBase):

    config_file = 'wsgi_sqlite.conf'

    def test_get(self):
        response = self.simulate_get('/v1/health')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

    def test_head(self):
        response = self.simulate_head('/v1/health')
        self.assertEqual(self.srmock.status, falcon.HTTP_204)
        self.assertEqual(response, [])

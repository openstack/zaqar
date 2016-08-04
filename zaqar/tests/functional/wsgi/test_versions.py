# Copyright (c) 2016 Red Hat, Inc.
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

from zaqar.tests.functional import base


class TestVersions(base.FunctionalTestBase):

    """Tests for Versions Resource."""

    server_class = base.ZaqarServer

    def setUp(self):
        super(TestVersions, self).setUp()
        self.base_url = "{url}/".format(url=self.cfg.zaqar.url)
        self.client.set_base_url(self.base_url)

    def test_get_versions_without_headers(self):
        result = self.client.get('', headers={})
        self.assertIn("versions", result.json())

    def test_get_versions_with_headers(self):
        result = self.client.get('')
        self.assertIn("versions", result.json())

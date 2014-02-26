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
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid

import falcon
from falcon import testing

from . import base  # noqa


class TestMediaType(base.TestBase):

    config_file = 'wsgi_sqlalchemy.conf'

    def test_json_only_endpoints(self):
        endpoints = (
            ('GET', self.url_prefix + '/queues'),
            ('GET', self.url_prefix + '/queues/nonexistent/metadata'),
            ('GET', self.url_prefix + '/queues/nonexistent/stats'),
            ('POST', self.url_prefix + '/queues/nonexistent/messages'),
            ('GET', self.url_prefix + '/queues/nonexistent/messages/deadbeaf'),
            ('POST', self.url_prefix + '/queues/nonexistent/claims'),
            ('GET', self.url_prefix + '/queues/nonexistent/claims/0ad'),
            ('GET', self.url_prefix + '/health'),
        )

        for method, endpoint in endpoints:
            headers = {
                'Client-ID': str(uuid.uuid4()),
                'Accept': 'application/xml',
            }

            env = testing.create_environ(endpoint,
                                         method=method,
                                         headers=headers)

            self.app(env, self.srmock)
            self.assertEqual(self.srmock.status, falcon.HTTP_406)

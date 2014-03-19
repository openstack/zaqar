# Copyright (c) 2013 Rackspace, Inc.
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

import json

import falcon
import six.moves.urllib.parse as urlparse

from . import base  # noqa


class TestHomeDocument(base.TestBase):

    config_file = 'wsgi_sqlalchemy.conf'

    def test_json_response(self):
        body = self.simulate_get(self.url_prefix)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)

        content_type = self.srmock.headers_dict['Content-Type']
        self.assertEqual(content_type, 'application/json-home')

        try:
            json.loads(body[0])
        except ValueError:
            self.fail('Home document is not valid JSON')

    def test_href_template(self):
        body = self.simulate_get(self.url_prefix)
        self.assertEqual(self.srmock.status, falcon.HTTP_200)
        resp = json.loads(body[0])
        queue_href_template = resp['resources']['rel/queue']['href-template']
        path_1 = 'https://marconi.example.com' + self.url_prefix
        path_2 = 'https://marconi.example.com' + self.url_prefix + '/'

        # Verify all the href template start with the correct version prefix
        for resource in list(resp['resources']):
            self.assertTrue(resp['resources'][resource]['href-template'].
                            startswith(self.url_prefix))

        url = urlparse.urljoin(path_1, queue_href_template)
        expected = ('https://marconi.example.com' + self.url_prefix +
                    '/queues/foo')
        self.assertEqual(url.format(queue_name='foo'), expected)

        url = urlparse.urljoin(path_2, queue_href_template)
        self.assertEqual(url.format(queue_name='foo'), expected)

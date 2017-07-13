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


import falcon
from falcon import testing
from oslo_serialization import jsonutils
from oslo_utils import uuidutils


from zaqar.tests.unit.transport.wsgi import base


class TestMediaType(base.V1Base):

    config_file = 'wsgi_mongodb.conf'

    def test_json_only_endpoints_with_wrong_accept_header(self):
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
                'Client-ID': uuidutils.generate_uuid(),
                'Accept': 'application/xml',
            }

            env = testing.create_environ(endpoint,
                                         method=method,
                                         headers=headers)

            self.app(env, self.srmock)
            self.assertEqual(falcon.HTTP_406, self.srmock.status)

    def test_request_with_body_and_urlencoded_contenttype_header_fails(self):
        # NOTE(Eva-i): this test case makes sure wsgi 'before' hook
        # "require_content_type_be_non_urlencoded" works to prevent
        # bug/1547100.
        eww_queue_path = self.url_prefix + '/queues/eww'
        eww_queue_messages_path = eww_queue_path + '/messages'
        sample_message = jsonutils.dumps([{'body': {'eww!'}, 'ttl': 200}])
        bad_headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        # Create queue request with bad headers. Should still work, because it
        # has no body.
        self.simulate_put(eww_queue_path, headers=bad_headers)
        self.addCleanup(self.simulate_delete, eww_queue_path,
                        headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # Post message request with good headers. Should work.
        self.simulate_post(eww_queue_messages_path, body=sample_message,
                           headers=self.headers)
        self.assertEqual(falcon.HTTP_201, self.srmock.status)

        # Post message request with bad headers. Should not work.
        self.simulate_post(eww_queue_messages_path, body=sample_message,
                           headers=bad_headers)
        self.assertEqual(falcon.HTTP_400, self.srmock.status)

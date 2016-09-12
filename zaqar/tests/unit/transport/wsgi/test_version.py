# Copyright (c) 2014 OpenStack Foundation
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
from oslo_serialization import jsonutils

from zaqar.tests.unit.transport.wsgi import base

EXPECTED_VERSIONS = [
    {
        'id': '1',
        'status': 'DEPRECATED',
        'updated': '2014-9-11T17:47:05Z',
        'media-types': [
            {
                'base': 'application/json',
                'type': 'application/vnd.openstack.messaging-v1+json'
            }
        ],
        'links': [
            {
                'href': '/v1/',
                'rel': 'self'
            }
        ]
    },
    {
        'id': '1.1',
        'status': 'DEPRECATED',
        'updated': '2016-7-29T02:22:47Z',
        'media-types': [
            {
                'base': 'application/json',
                'type': 'application/vnd.openstack.messaging-v1_1+json'
            }
        ],
        'links': [
            {
                'href': '/v1.1/',
                'rel': 'self'
            }
        ]
    },
    {
        'id': '2',
        'status': 'CURRENT',
        'updated': '2014-9-24T04:06:47Z',
        'media-types': [
            {
                'base': 'application/json',
                'type': 'application/vnd.openstack.messaging-v2+json'
            }
        ],
        'links': [
            {
                'href': '/v2/',
                'rel': 'self'
            }
        ]
    }
]


class TestVersion(base.TestBase):

    config_file = 'wsgi_mongodb.conf'

    def test_get(self):
        response = self.simulate_get('/')
        versions = jsonutils.loads(response[0])['versions']

        self.assertEqual(falcon.HTTP_300, self.srmock.status)
        self.assertEqual(3, len(versions))
        self.assertEqual(EXPECTED_VERSIONS, versions)

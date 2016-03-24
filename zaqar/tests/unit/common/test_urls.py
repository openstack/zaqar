# Copyright (c) 2015 Red Hat, Inc.
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

import datetime
import hashlib
import hmac

from oslo_utils import timeutils
import six

from zaqar.common import urls
from zaqar.tests import base


class TestURLs(base.TestBase):

    def test_create_signed_url(self):
        timeutils.set_time_override()
        self.addCleanup(timeutils.clear_time_override)

        key = six.b('test')
        methods = ['POST']
        project = 'my-project'
        paths = ['/v2/queues/shared/messages']
        expires = timeutils.utcnow() + datetime.timedelta(days=1)
        expires_str = expires.strftime(urls._DATE_FORMAT)

        hmac_body = six.b(r'%(paths)s\n%(methods)s\n'
                          r'%(project)s\n%(expires)s' %
                          {'paths': ','.join(paths),
                           'methods': ','.join(methods),
                           'project': project, 'expires': expires_str})

        expected = hmac.new(key, hmac_body, hashlib.sha256).hexdigest()
        actual = urls.create_signed_url(key, paths, methods=['POST'],
                                        project=project)
        self.assertEqual(expected, actual['signature'])

    def test_create_signed_url_multiple_paths(self):
        timeutils.set_time_override()
        self.addCleanup(timeutils.clear_time_override)

        key = six.b('test')
        methods = ['POST']
        project = 'my-project'
        paths = ['/v2/queues/shared/messages',
                 '/v2/queues/shared/subscriptions']
        expires = timeutils.utcnow() + datetime.timedelta(days=1)
        expires_str = expires.strftime(urls._DATE_FORMAT)

        hmac_body = six.b(r'%(paths)s\n%(methods)s\n'
                          r'%(project)s\n%(expires)s' %
                          {'paths': ','.join(paths),
                           'methods': ','.join(methods),
                           'project': project, 'expires': expires_str})

        expected = hmac.new(key, hmac_body, hashlib.sha256).hexdigest()
        actual = urls.create_signed_url(key, paths, methods=['POST'],
                                        project=project)
        self.assertEqual(expected, actual['signature'])

    def test_create_signed_url_utc(self):
        """Test that the method converts the TZ to UTC."""
        date_str = '2100-05-31T19:00:17+02'
        date_str_utc = '2100-05-31T17:00:17'

        key = six.b('test')
        project = None
        methods = ['GET']
        paths = ['/v2/queues/shared/messages']
        parsed = timeutils.parse_isotime(date_str_utc)
        expires = timeutils.normalize_time(parsed)
        expires_str = expires.strftime(urls._DATE_FORMAT)

        hmac_body = six.b('%(paths)s\\n%(methods)s\\n'
                          '%(project)s\\n%(expires)s' %
                          {'paths': ','.join(paths),
                           'methods': ','.join(methods),
                           'project': project, 'expires': expires_str})

        expected = hmac.new(key, hmac_body, hashlib.sha256).hexdigest()
        actual = urls.create_signed_url(key, paths, expires=date_str)
        self.assertEqual(expected, actual['signature'])

    def test_create_signed_urls_validation(self):
        self.assertRaises(ValueError, urls.create_signed_url, None, ['/test'])
        self.assertRaises(ValueError, urls.create_signed_url, 'test', None)
        self.assertRaises(ValueError, urls.create_signed_url, 'test',
                          ['/test'], methods='not list')
        self.assertRaises(ValueError, urls.create_signed_url, 'test', [])
        self.assertRaises(ValueError, urls.create_signed_url, 'test', '/test')
        self.assertRaises(ValueError, urls.create_signed_url, 'test',
                          ['/test'], expires='wrong date format')
        self.assertRaises(ValueError, urls.create_signed_url, 'test',
                          ['/test'], expires='3600')

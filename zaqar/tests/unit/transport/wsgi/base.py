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

import falcon
from falcon import testing as ftest
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from zaqar import bootstrap
from zaqar.conf import default
from zaqar.conf import drivers_transport_wsgi
from zaqar.conf import transport
from zaqar import tests as testing


class TestBase(testing.TestBase):

    config_file = None

    def setUp(self):
        super().setUp()

        if not self.config_file:
            self.skipTest("No config specified")

        self.conf.register_opts(default.ALL_OPTS)
        self.conf.register_opts(transport.ALL_OPTS,
                                group=transport.GROUP_NAME)
        self.transport_cfg = self.conf[transport.GROUP_NAME]

        self.conf.register_opts(drivers_transport_wsgi.ALL_OPTS,
                                group=drivers_transport_wsgi.GROUP_NAME)
        self.wsgi_cfg = self.conf[drivers_transport_wsgi.GROUP_NAME]

        self.conf.unreliable = True
        self.conf.admin_mode = True
        self.boot = bootstrap.Bootstrap(self.conf)
        self.addCleanup(self.boot.storage.close)
        self.addCleanup(self.boot.control.close)

        self.app = self.boot.transport.app

        self.srmock = ftest.StartResponseMock()

        self.headers = {
            'Client-ID': uuidutils.generate_uuid(),
            'X-ROLES': 'admin',
            'X-USER-ID': 'a12d157c7d0d41999096639078fd11fc',
            'X-TENANT-ID': 'abb69142168841fcaa2785791b92467f',
        }

    def tearDown(self):
        if self.conf.pooling:
            self.boot.control.pools_controller.drop_all()
            self.boot.control.catalogue_controller.drop_all()
        super().tearDown()

    def simulate_request(self, path, project_id=None, **kwargs):
        """Simulate a request.

        Simulates a WSGI request to the API for testing.

        :param path: Request path for the desired resource
        :param project_id: Project ID to use for the X-Project-ID header,
            or None to not set the header
        :param kwargs: Same as falcon.testing.create_environ()

        :returns: standard WSGI iterable response
        """

        # NOTE(flaper87): We create a copy regardless the headers
        # were passed or not. This will prevent modifying `self.headers`
        # in cases where simulate methods are called like:
        # self.simulate_put(path, headers=self.headers)
        headers = kwargs.get('headers', self.headers).copy()
        project_id = ('518b51ea133c4facadae42c328d6b77b' if project_id
                      is None else project_id)
        if kwargs.get('need_project_id', True):
            headers['X-Project-ID'] = headers.get('X-Project-ID', project_id)
        kwargs.pop('need_project_id', None)
        kwargs['headers'] = headers
        kwargs['host'] = 'openstack.example.com'
        kwargs['root_path'] = 'messaging'
        try:
            path.encode('latin1').decode('utf-8', 'replace')
        except UnicodeEncodeError:
            self.srmock.status = falcon.HTTP_400
            return

        return self.app(ftest.create_environ(path=path, **kwargs),
                        self.srmock)

    def simulate_get(self, *args, **kwargs):
        """Simulate a GET request."""
        kwargs['method'] = 'GET'
        return self.simulate_request(*args, **kwargs)

    def simulate_head(self, *args, **kwargs):
        """Simulate a HEAD request."""
        kwargs['method'] = 'HEAD'
        return self.simulate_request(*args, **kwargs)

    def simulate_put(self, *args, **kwargs):
        """Simulate a PUT request."""
        kwargs['method'] = 'PUT'
        return self.simulate_request(*args, **kwargs)

    def simulate_post(self, *args, **kwargs):
        """Simulate a POST request."""
        kwargs['method'] = 'POST'
        return self.simulate_request(*args, **kwargs)

    def simulate_delete(self, *args, **kwargs):
        """Simulate a DELETE request."""
        kwargs['method'] = 'DELETE'
        return self.simulate_request(*args, **kwargs)

    def simulate_patch(self, *args, **kwargs):
        """Simulate a PATCH request."""
        kwargs['method'] = 'PATCH'
        return self.simulate_request(*args, **kwargs)


class TestBaseFaulty(TestBase):
    """This test ensures we aren't letting any exceptions go unhandled."""


class V2Base(TestBase):
    """Base class for V2 API Tests.

    Should contain methods specific to V2 of the API
    """
    url_prefix = '/v2'

    def _empty_message_list(self, body):
        self.assertEqual([], jsonutils.loads(body[0])['messages'])


class V2BaseFaulty(TestBaseFaulty):
    """Base class for V2 API Faulty Tests.

    Should contain methods specific to V2 exception testing
    """
    url_prefix = '/v2'

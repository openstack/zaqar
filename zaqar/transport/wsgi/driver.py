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

import functools
from wsgiref import simple_server

import falcon
from oslo_config import cfg

from zaqar.common import decorators
from zaqar.common.transport.wsgi import helpers
from zaqar.i18n import _
import zaqar.openstack.common.log as logging
from zaqar import transport
from zaqar.transport import auth
from zaqar.transport import validation
from zaqar.transport.wsgi import v1_0
from zaqar.transport.wsgi import v1_1
from zaqar.transport.wsgi import v2_0
from zaqar.transport.wsgi import version

_WSGI_OPTIONS = (
    cfg.StrOpt('bind', default='127.0.0.1',
               help='Address on which the self-hosting server will listen.'),

    cfg.IntOpt('port', default=8888,
               help='Port on which the self-hosting server will listen.'),
)

_WSGI_GROUP = 'drivers:transport:wsgi'

LOG = logging.getLogger(__name__)


def _config_options():
    return [(_WSGI_GROUP, _WSGI_OPTIONS)]


class Driver(transport.DriverBase):

    def __init__(self, conf, storage, cache, control):
        super(Driver, self).__init__(conf, storage, cache, control)

        self._conf.register_opts(_WSGI_OPTIONS, group=_WSGI_GROUP)
        self._wsgi_conf = self._conf[_WSGI_GROUP]
        self._validate = validation.Validator(self._conf)

        self.app = None
        self._init_routes()
        self._init_middleware()

    @decorators.lazy_property(write=False)
    def before_hooks(self):
        """Exposed to facilitate unit testing."""
        return [
            helpers.require_accepts_json,
            helpers.require_client_id,
            helpers.extract_project_id,

            # NOTE(jeffrey4l): Depends on the project_id and client_id being
            # extracted above
            helpers.inject_context,

            # NOTE(kgriffs): Depends on project_id being extracted, above
            functools.partial(helpers.validate_queue_identification,
                              self._validate.queue_identification)
        ]

    def _init_routes(self):
        """Initialize hooks and URI routes to resources."""

        catalog = [
            ('/v1', v1_0.public_endpoints(self, self._conf)),
            ('/v1.1', v1_1.public_endpoints(self, self._conf)),
            ('/v2', v2_0.public_endpoints(self, self._conf)),
            ('/', [('', version.Resource())])
        ]

        if self._conf.admin_mode:
            catalog.extend([
                ('/v1', v1_0.private_endpoints(self, self._conf)),
                ('/v1.1', v1_1.private_endpoints(self, self._conf)),
                ('/v2', v2_0.private_endpoints(self, self._conf)),
            ])

        self.app = falcon.API(before=self.before_hooks)

        for version_path, endpoints in catalog:
            for route, resource in endpoints:
                self.app.add_route(version_path + route, resource)

    def _init_middleware(self):
        """Initialize WSGI middlewarez."""

        # NOTE(flaper87): Install Auth
        if self._conf.auth_strategy:
            strategy = auth.strategy(self._conf.auth_strategy)
            self.app = strategy.install(self.app, self._conf)

    def listen(self):
        """Self-host using 'bind' and 'port' from the WSGI config group."""

        msgtmpl = _(u'Serving on host %(bind)s:%(port)s')
        LOG.info(msgtmpl,
                 {'bind': self._wsgi_conf.bind, 'port': self._wsgi_conf.port})

        httpd = simple_server.make_server(self._wsgi_conf.bind,
                                          self._wsgi_conf.port,
                                          self.app)
        httpd.serve_forever()

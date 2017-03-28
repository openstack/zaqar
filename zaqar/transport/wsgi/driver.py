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

from distutils import version as d_version
import falcon
import six
import socket
from wsgiref import simple_server

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import netutils

from zaqar.common import decorators
from zaqar.common.transport.wsgi import helpers
from zaqar.i18n import _
from zaqar import transport
from zaqar.transport import acl
from zaqar.transport.middleware import auth
from zaqar.transport.middleware import cors
from zaqar.transport.middleware import profile
from zaqar.transport import validation
from zaqar.transport.wsgi import v1_0
from zaqar.transport.wsgi import v1_1
from zaqar.transport.wsgi import v2_0
from zaqar.transport.wsgi import version

_WSGI_OPTIONS = (
    cfg.HostAddressOpt('bind', default='127.0.0.1',
                       help='Address on which the self-hosting server will '
                            'listen.'),

    cfg.PortOpt('port', default=8888,
                help='Port on which the self-hosting server will listen.'),
)

_WSGI_GROUP = 'drivers:transport:wsgi'

LOG = logging.getLogger(__name__)


def _config_options():
    return [(_WSGI_GROUP, _WSGI_OPTIONS)]


class FuncMiddleware(object):

    def __init__(self, func):
        self.func = func

    def process_resource(self, req, resp, resource, params):
        return self.func(req, resp, params)


class Driver(transport.DriverBase):

    def __init__(self, conf, storage, cache, control):
        super(Driver, self).__init__(conf, storage, cache, control)

        self._conf.register_opts(_WSGI_OPTIONS, group=_WSGI_GROUP)
        self._wsgi_conf = self._conf[_WSGI_GROUP]
        self._validate = validation.Validator(self._conf)

        self.app = None
        self._init_routes()
        self._init_middleware()

    def _verify_pre_signed_url(self, req, resp, params):
        return helpers.verify_pre_signed_url(self._conf.signed_url.secret_key,
                                             req, resp, params)

    def _validate_queue_identification(self, req, resp, params):
        return helpers.validate_queue_identification(
            self._validate.queue_identification, req, resp, params)

    @decorators.lazy_property(write=False)
    def before_hooks(self):
        """Exposed to facilitate unit testing."""
        return [
            self._verify_pre_signed_url,
            helpers.require_content_type_be_non_urlencoded,
            helpers.require_accepts_json,
            helpers.require_client_id,
            helpers.extract_project_id,

            # NOTE(jeffrey4l): Depends on the project_id and client_id being
            # extracted above
            helpers.inject_context,

            # NOTE(kgriffs): Depends on project_id being extracted, above
            self._validate_queue_identification
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

        # NOTE(wanghao): Since hook feature has removed after 1.0.0, using
        # middleware instead of it, but for the compatibility with old version,
        # we support them both now. Hook way can be removed after falcon
        # version must be bigger than 1.0.0 in requirements.
        if (d_version.LooseVersion(falcon.__version__) >=
                d_version.LooseVersion("1.0.0")):
            middleware = [FuncMiddleware(hook) for hook in self.before_hooks]
            self.app = falcon.API(middleware=middleware)
        else:
            self.app = falcon.API(before=self.before_hooks)

        self.app.add_error_handler(Exception, self._error_handler)

        for version_path, endpoints in catalog:
            if endpoints:
                for route, resource in endpoints:
                    self.app.add_route(version_path + route, resource)

    def _init_middleware(self):
        """Initialize WSGI middlewarez."""

        # NOTE(zhiyan): Install Profiler
        if (self._conf.profiler.enabled and
                self._conf.profiler.trace_wsgi_transport):
            self.app = profile.install_wsgi_tracer(self.app, self._conf)

        auth_app = self.app
        # NOTE(flaper87): Install Auth
        if self._conf.auth_strategy:
            strategy = auth.strategy(self._conf.auth_strategy)
            auth_app = strategy.install(self.app, self._conf)

        self.app = auth.SignedHeadersAuth(self.app, auth_app)

        # NOTE(wangxiyuan): Install CORS, this middleware should be called
        # before Keystone auth.
        self.app = cors.install_cors(self.app, auth_app, self._conf)

        acl.setup_policy(self._conf)

    def _error_handler(self, exc, request, response, params):
        if isinstance(exc, falcon.HTTPError):
            raise exc
        LOG.exception(exc)
        raise falcon.HTTPInternalServerError('Internal server error',
                                             six.text_type(exc))

    def _get_server_cls(self, host):
        """Return an appropriate WSGI server class base on provided host

        :param host: The listen host for the zaqar API server.
        """
        server_cls = simple_server.WSGIServer
        if netutils.is_valid_ipv6(host):
            if getattr(server_cls, 'address_family') == socket.AF_INET:
                class server_cls(server_cls):
                    address_family = socket.AF_INET6
        return server_cls

    def listen(self):
        """Self-host using 'bind' and 'port' from the WSGI config group."""

        msgtmpl = _(u'Serving on host %(bind)s:%(port)s')
        LOG.info(msgtmpl,
                 {'bind': self._wsgi_conf.bind, 'port': self._wsgi_conf.port})
        server_cls = self._get_server_cls(self._wsgi_conf.bind)
        httpd = simple_server.make_server(self._wsgi_conf.bind,
                                          self._wsgi_conf.port,
                                          self.app,
                                          server_cls)
        httpd.serve_forever()

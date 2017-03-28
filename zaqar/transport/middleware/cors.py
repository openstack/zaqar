# Copyright 2017 OpenStack, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import six.moves.urllib.parse as urlparse
import webob

from oslo_log import log
from oslo_middleware import cors

LOG = log.getLogger(__name__)


class Response(webob.Response):

    def __call__(self, environ, start_response):
        """WSGI application interface"""

        if self.conditional_response:
            return self.conditional_response_app(environ, start_response)
        headerlist = self._abs_headerlist(environ)
        start_response(self.status, headerlist)
        if environ['REQUEST_METHOD'] == 'HEAD':
            # Special case here...
            # NOTE(wangxiyuan): webob.response.Response always return
            # EmptyResponse here. This behavior breaks backward-compatibility.
            # so we need to 'fix' it here manually.
            return []
        return self._app_iter

    def _abs_headerlist(self, *args, **kwargs):
        headerlist = super(Response, self)._abs_headerlist(*args, **kwargs)

        # NOTE(wangxiyuan): webob.response.Response always convert relative
        # path to absolute path given the request environ on location field in
        # the header of response. This behavior breaks backward-compatibility.
        # so we need to 'fix' it here manually.
        for i, (name, value) in enumerate(headerlist):
            if name.lower() == 'location':
                loc = urlparse.urlparse(value)
                relative_path = value[value.index(loc.path):]
                headerlist[i] = (name, relative_path)
                break

        return headerlist


class Request(webob.Request):

    ResponseClass = Response


class CORSMiddleware(object):

    def __init__(self, app, auth_app, conf):
        self._app = cors.CORS(app, conf)

        # We don't auth here. It's just used for keeping consistence.
        self._auth_app = auth_app

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, request):
        return self._app(request)

    @classmethod
    def install(cls, app, auth_app, conf):

        LOG.debug(u'Installing CORS middleware.')
        cors.set_defaults(
            allow_headers=['X-Auth-Token',
                           'X-Identity-Status',
                           'X-Roles',
                           'X-Service-Catalog',
                           'X-User-Id',
                           'X-Tenant-Id',
                           'X-OpenStack-Request-ID',
                           'X-Trace-Info',
                           'X-Trace-HMAC',
                           'Client-id'],
            expose_headers=['X-Auth-Token',
                            'X-Subject-Token',
                            'X-Service-Token',
                            'X-OpenStack-Request-ID'],
            allow_methods=['GET',
                           'PUT',
                           'POST',
                           'DELETE',
                           'PATCH',
                           'HEAD']
        )
        return CORSMiddleware(app, auth_app, conf)


def install_cors(app, auth_app, conf):
    return CORSMiddleware.install(app, auth_app, conf)

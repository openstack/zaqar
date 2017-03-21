# Copyright 2016 OpenStack, Inc.
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

import six
import six.moves.urllib.parse as urlparse
import webob

from oslo_log import log
from osprofiler import _utils as utils
from osprofiler import notifier
from osprofiler import profiler
from osprofiler import web

LOG = log.getLogger(__name__)


def setup(conf, binary, host):
    if conf.profiler.enabled:

        # Note(wangxiyuan): OSprofiler now support some kind of backends, such
        # as Ceilometer, ElasticSearch, Messaging and MongoDB.
        # 1. Ceilometer is only used for data collection, and Messaging is only
        # used for data transfer. So Ceilometer only works when Messaging is
        # enabled.
        # 2. ElasticSearch and MongoDB support both data collection and
        # transfer. So they can be used standalone.
        # 3. Choose which backend depends on the config option
        # "connection_string" , and the default value is "messaging://".
        backend_uri = conf.profiler.connection_string
        if "://" not in backend_uri:
            backend_uri += "://"
        parsed_connection = urlparse.urlparse(backend_uri)
        backend_type = parsed_connection.scheme
        if backend_type == "messaging":
            import oslo_messaging
            _notifier = notifier.create(
                backend_uri, oslo_messaging, {},
                oslo_messaging.get_notification_transport(conf),
                "Zaqar", binary, host)
        else:
            _notifier = notifier.create(backend_uri, project="Zaqar",
                                        service=binary, host=host)
        notifier.set(_notifier)
        LOG.warning("OSProfiler is enabled.\nIt means that person who "
                    "knows any of hmac_keys that are specified in "
                    "/etc/zaqar/zaqar.conf can trace his requests. \n In "
                    "real life only operator can read this file so there "
                    "is no security issue. Note that even if person can "
                    "trigger profiler, only admin user can retrieve trace "
                    "information.\n"
                    "To disable OSprofiler set in zaqar.conf:\n"
                    "[profiler]\nenabled=false")
        web.enable(conf.profiler.hmac_keys)
    else:
        web.disable()


class ProfileWSGIMiddleware(object):

    def __init__(self, application, hmac_keys=None, enabled=False):
        self.application = application
        self.name = "wsgi"
        self.enabled = enabled
        self.hmac_keys = utils.split(hmac_keys or "")

    def _trace_is_valid(self, trace_info):
        if not isinstance(trace_info, dict):
            return False
        trace_keys = set(six.iterkeys(trace_info))
        if not all(k in trace_keys for k in web._REQUIRED_KEYS):
            return False
        if trace_keys.difference(web._REQUIRED_KEYS + web._OPTIONAL_KEYS):
            return False
        return True

    def __call__(self, environ, start_response):
        request = webob.Request(environ)
        trace_info = utils.signed_unpack(request.headers.get(web.X_TRACE_INFO),
                                         request.headers.get(web.X_TRACE_HMAC),
                                         self.hmac_keys)

        if not self._trace_is_valid(trace_info):
            return self.application(environ, start_response)

        profiler.init(**trace_info)
        info = {
            "request": {
                "path": request.path,
                "query": request.query_string,
                "method": request.method,
                "scheme": request.scheme
            }
        }
        with profiler.Trace(self.name, info=info):
            return self.application(environ, start_response)


def install_wsgi_tracer(app, conf):
    enabled = conf.profiler.enabled and conf.profiler.trace_wsgi_transport

    if enabled:
        LOG.debug(u'Installing osprofiler\'s wsgi tracer')

    return ProfileWSGIMiddleware(app, conf.profiler.hmac_keys, enabled=enabled)

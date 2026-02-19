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

from oslo_log import log
from osprofiler import initializer
from osprofiler import web

LOG = log.getLogger(__name__)


def setup(conf, binary, host):
    initializer.init_from_conf(context=None, project='Zaqar', service=binary,
                               host=host, conf=conf)


def install_wsgi_tracer(app, conf):
    enabled = conf.profiler.enabled and conf.profiler.trace_wsgi_transport
    return web.WsgiMiddleware(app, enabled=enabled)

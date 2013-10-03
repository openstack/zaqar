# Copyright (c) 2013 Red Hat, Inc.
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

from oslo.config import cfg

_WSGI_OPTIONS = [
    cfg.StrOpt('bind', default='0.0.0.0',
               help='Address to bind this server to'),

    cfg.IntOpt('port', default=8888,
               help='Port to bind this server to'),

    cfg.IntOpt('content_max_length', default=256 * 1024),
    cfg.IntOpt('metadata_max_length', default=64 * 1024)
]

cfg.CONF.register_opts(_WSGI_OPTIONS, group='queues:drivers:transport:wsgi')

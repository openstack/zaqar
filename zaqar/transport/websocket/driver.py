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

from oslo_config import cfg
from oslo_log import log as logging

try:
    import asyncio
except ImportError:
    import trollius as asyncio

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar.transport.websocket import factory


_WS_OPTIONS = (
    cfg.StrOpt('bind', default='127.0.0.1',
               help='Address on which the self-hosting server will listen.'),

    cfg.IntOpt('port', default=9000,
               help='Port on which the self-hosting server will listen.'),

    cfg.IntOpt('external-port', default=None,
               help='Port on which the service is provided to the user.'),

    cfg.BoolOpt('debug', default=False, help='Print debugging output')
)

_WS_GROUP = 'drivers:transport:websocket'

LOG = logging.getLogger(__name__)


def _config_options():
    return [(_WS_GROUP, _WS_OPTIONS)]


class Driver(object):

    def __init__(self, conf, api, cache):
        self._conf = conf
        self._api = api
        self._cache = cache

        self._conf.register_opts(_WS_OPTIONS, group=_WS_GROUP)
        self._ws_conf = self._conf[_WS_GROUP]

    @decorators.lazy_property(write=False)
    def factory(self):
        uri = 'ws://' + self._ws_conf.bind + ':' + str(self._ws_conf.port)
        return factory.ProtocolFactory(
            uri, debug=self._ws_conf.debug, handler=self._api,
            external_port=self._ws_conf.external_port)

    def listen(self):
        """Self-host using 'bind' and 'port' from the WS config group."""

        msgtmpl = _(u'Serving on host %(bind)s:%(port)s')
        LOG.info(msgtmpl,
                 {'bind': self._ws_conf.bind, 'port': self._ws_conf.port})

        loop = asyncio.get_event_loop()
        coro = loop.create_server(self.factory,
                                  self._ws_conf.bind,
                                  self._ws_conf.port)
        server = loop.run_until_complete(coro)

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.close()
            loop.close()

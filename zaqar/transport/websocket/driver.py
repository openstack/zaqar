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

from autobahn.asyncio import websocket
from oslo.config import cfg

try:
    import asyncio
except ImportError:
    import trollius as asyncio

from zaqar.i18n import _
import zaqar.openstack.common.log as logging
from zaqar.transport.websocket import protocol

_WS_OPTIONS = (
    cfg.StrOpt('bind', default='127.0.0.1',
               help='Address on which the self-hosting server will listen.'),

    cfg.IntOpt('port', default=9000,
               help='Port on which the self-hosting server will listen.'),

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

    def listen(self):
        """Self-host using 'bind' and 'port' from the WS config group."""

        msgtmpl = _(u'Serving on host %(bind)s:%(port)s')
        LOG.info(msgtmpl,
                 {'bind': self._ws_conf.bind, 'port': self._ws_conf.port})

        uri = 'ws://' + self._ws_conf.bind + ':' + str(self._ws_conf.port)
        factory = websocket.WebSocketServerFactory(uri,
                                                   debug=self._ws_conf.debug)
        factory.protocol = protocol.MessagingProtocol

        loop = asyncio.get_event_loop()
        coro = loop.create_server(factory, self._ws_conf.bind,
                                  self._ws_conf.port)
        server = loop.run_until_complete(coro)

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.close()
            loop.close()

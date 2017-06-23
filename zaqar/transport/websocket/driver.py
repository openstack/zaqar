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

import socket

from oslo_config import cfg
from oslo_log import log as logging

try:
    import asyncio
except ImportError:
    import trollius as asyncio

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar.transport import base
from zaqar.transport.middleware import auth
from zaqar.transport.websocket import factory


_WS_OPTIONS = (
    cfg.HostAddressOpt('bind', default='127.0.0.1',
                       help='Address on which the self-hosting server will '
                            'listen.'),

    cfg.PortOpt('port', default=9000,
                help='Port on which the self-hosting server will listen.'),

    cfg.PortOpt('external-port',
                help='Port on which the service is provided to the user.'),

    cfg.HostAddressOpt('notification-bind',
                       help='Address on which the notification server will '
                            'listen.'),

    cfg.PortOpt('notification-port', default=0,
                help='Port on which the notification server will listen.'),

)

_WS_GROUP = 'drivers:transport:websocket'

LOG = logging.getLogger(__name__)


def _config_options():
    return [(_WS_GROUP, _WS_OPTIONS)]


class Driver(base.DriverBase):

    def __init__(self, conf, api, cache):
        super(Driver, self).__init__(conf, None, None, None)
        self._api = api
        self._cache = cache

        self._conf.register_opts(_WS_OPTIONS, group=_WS_GROUP)
        self._ws_conf = self._conf[_WS_GROUP]

        if self._conf.auth_strategy:
            auth_strategy = auth.strategy(self._conf.auth_strategy)
            self._auth_strategy = lambda app: auth_strategy.install(
                app, self._conf)
        else:
            self._auth_strategy = None

    @decorators.lazy_property(write=False)
    def factory(self):
        uri = 'ws://' + self._ws_conf.bind + ':' + str(self._ws_conf.port)
        return factory.ProtocolFactory(
            uri,
            handler=self._api,
            external_port=self._ws_conf.external_port,
            auth_strategy=self._auth_strategy,
            loop=asyncio.get_event_loop(),
            secret_key=self._conf.signed_url.secret_key)

    @decorators.lazy_property(write=False)
    def notification_factory(self):
        return factory.NotificationFactory(self.factory)

    def listen(self):
        """Self-host the WebSocket server.

        It runs the WebSocket server using 'bind' and 'port' options from the
        websocket config group, and the notifiton endpoint using the
        'notification_bind' and 'notification_port' options.
        """
        msgtmpl = _(u'Serving on host %(bind)s:%(port)s')
        LOG.info(msgtmpl,
                 {'bind': self._ws_conf.bind, 'port': self._ws_conf.port})

        loop = asyncio.get_event_loop()
        coro_notification = loop.create_server(
            self.notification_factory,
            self._ws_conf.notification_bind,
            self._ws_conf.notification_port)
        coro = loop.create_server(
            self.factory,
            self._ws_conf.bind,
            self._ws_conf.port)

        def got_server(task):
            # Retrieve the port number of the listening socket
            port = task.result().sockets[0].getsockname()[1]
            if self._ws_conf.notification_bind is not None:
                host = self._ws_conf.notification_bind
            else:
                host = socket.gethostname()
            self.notification_factory.set_subscription_url(
                'http://%s:%s/' % (host, port))
            self._api.set_subscription_factory(self.notification_factory)

        task = asyncio.Task(coro_notification)
        task.add_done_callback(got_server)

        loop.run_until_complete(asyncio.wait([coro, task]))

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

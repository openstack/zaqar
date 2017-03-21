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

import datetime
import io
import json
import sys

from autobahn.asyncio import websocket
import msgpack
from oslo_log import log as logging
from oslo_utils import timeutils
import pytz
import txaio

try:
    import asyncio
except ImportError:
    import trollius as asyncio

try:
    import mimetools
    Message = mimetools.Message
except ImportError:
    from email.mime import message
    Message = message.MIMEMessage

from zaqar.common import consts


LOG = logging.getLogger(__name__)


class MessagingProtocol(websocket.WebSocketServerProtocol):

    _fake_env = {
        'REQUEST_METHOD': 'POST',
        'SERVER_NAME': 'zaqar',
        'SERVER_PORT': 80,
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'PATH_INFO': '/',
        'SCRIPT_NAME': '',
        'wsgi.url_scheme': 'http'
    }

    def __init__(self, handler, proto_id, auth_strategy, loop):
        txaio.use_asyncio()
        websocket.WebSocketServerProtocol.__init__(self)
        self._handler = handler
        self.proto_id = proto_id
        self._auth_strategy = auth_strategy
        self._loop = loop
        self._authentified = False
        self._auth_env = None
        self._auth_app = None
        self._auth_in_binary = None
        self._deauth_handle = None
        self.notify_in_binary = None
        self._subscriptions = []

    def onConnect(self, request):
        LOG.info("Client connecting: %s", request.peer)

    def onOpen(self):
        LOG.info("WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        # Deserialize the request
        try:
            if isBinary:
                payload = msgpack.unpackb(payload, encoding='utf-8')
            else:
                payload = json.loads(payload)
        except Exception:
            if isBinary:
                pack_name = 'binary (MessagePack)'
            else:
                pack_name = 'text (JSON)'
            ex_type, ex_value = sys.exc_info()[:2]
            ex_name = ex_type.__name__
            msg = 'Can\'t decode {0} request. {1}: {2}'.format(
                pack_name, ex_name, ex_value)
            LOG.debug(msg)
            body = {'error': msg}
            resp = self._handler.create_response(400, body)
            return self._send_response(resp, isBinary)
        # Check if the request is dict
        if not isinstance(payload, dict):
            body = {
                'error': 'Unexpected body type. Expected dict or dict like.'
            }
            resp = self._handler.create_response(400, body)
            return self._send_response(resp, isBinary)
        # Parse the request
        req = self._handler.create_request(payload, self._auth_env)
        # Validate and process the request
        resp = self._handler.validate_request(payload, req)
        if resp is None:
            if self._auth_strategy and not self._authentified:
                if self._auth_app or payload.get('action') != 'authenticate':
                    if 'URL-Signature' in payload.get('headers', {}):
                        if self._handler.verify_signature(
                                self.factory._secret_key, payload):
                            resp = self._handler.process_request(req, self)
                        else:
                            body = {'error': 'Not authentified.'}
                            resp = self._handler.create_response(
                                403, body, req)
                    else:
                        body = {'error': 'Not authentified.'}
                        resp = self._handler.create_response(403, body, req)
                else:
                    return self._authenticate(payload, isBinary)
            elif payload.get('action') == 'authenticate':
                return self._authenticate(payload, isBinary)
            else:
                resp = self._handler.process_request(req, self)
            if payload.get('action') == consts.SUBSCRIPTION_CREATE:
                # NOTE(Eva-i): this will make further websocket
                # notifications encoded in the same format as the last
                # successful websocket subscription create request.
                if resp._headers['status'] == 201:
                    subscriber = payload['body'].get('subscriber')
                    # If there is no subscriber, the user has created websocket
                    # subscription.
                    if not subscriber:
                        self.notify_in_binary = isBinary
                        self._subscriptions.append(resp)
        return self._send_response(resp, isBinary)

    def onClose(self, wasClean, code, reason):
        self._handler.clean_subscriptions(self._subscriptions)
        self.factory.unregister(self.proto_id)
        LOG.info("WebSocket connection closed: %s", reason)

    def _authenticate(self, payload, in_binary):
        self._auth_in_binary = in_binary
        self._auth_app = self._auth_strategy(self._auth_start)
        env = self._fake_env.copy()
        env.update(
            (self._header_to_env_var(key), value)
            for key, value in payload.get('headers').items())
        self._auth_app(env, self._auth_response)

    def _auth_start(self, env, start_response):
        self._authentified = True
        self._auth_env = dict(
            (self._env_var_to_header(key), value)
            for key, value in env.items())
        self._auth_app = None
        expire = env['keystone.token_info']['token']['expires_at']
        expire_time = timeutils.parse_isotime(expire)
        now = datetime.datetime.now(tz=pytz.UTC)
        delta = (expire_time - now).total_seconds()
        if self._deauth_handle is not None:
            self._deauth_handle.cancel()
        self._deauth_handle = self._loop.call_later(
            delta, self._deauthenticate)

        start_response('200 OK', [])

    def _deauthenticate(self):
        self._authentified = False
        self._auth_env = None
        self.sendClose(4003, u'Authentication expired.')

    def _auth_response(self, status, message):
        code = int(status.split()[0])
        req = self._handler.create_request({'action': 'authenticate'})
        if code != 200:
            # NOTE(wangxiyuan): _auth_app should be cleaned up the after the
            # authentication failure so that the client can be authenticated
            # again.
            self._auth_app = None
            body = {'error': 'Authentication failed.'}
            resp = self._handler.create_response(code, body, req)
            self._send_response(resp, self._auth_in_binary)
        else:
            body = {'message': 'Authentified.'}
            resp = self._handler.create_response(200, body, req)
            self._send_response(resp, self._auth_in_binary)

    def _header_to_env_var(self, key):
        return 'HTTP_%s' % key.replace('-', '_').upper()

    def _env_var_to_header(self, key):
        if key.startswith("HTTP_"):
            return key[5:].replace("_", "-")
        else:
            return key

    def _send_response(self, resp, in_binary):
        if in_binary:
            pack_name = 'bin'
            self.sendMessage(msgpack.packb(resp.get_response()), True)
        else:
            pack_name = 'txt'
            self.sendMessage(json.dumps(resp.get_response()), False)
        if LOG.isEnabledFor(logging.INFO):
            api = resp._request._api
            status = resp._headers['status']
            action = resp._request._action
            # Dump to JSON to print body without unicode prefixes on Python 2
            body = json.dumps(resp._request._body)
            var_dict = {'api': api, 'pack_name': pack_name, 'status':
                        status, 'action': action, 'body': body}
            LOG.info('Response: API %(api)s %(pack_name)s, %(status)s. '
                     'Request: action "%(action)s", body %(body)s.',
                     var_dict)


class NotificationProtocol(asyncio.Protocol):

    def __init__(self, factory):
        self._factory = factory

    def connection_made(self, transport):
        self._transport = transport
        self._data = bytearray()
        self._state = 'INIT'
        self._subscriber_id = None
        self._length = 0

    def write_status(self, status):
        self._transport.write(b'HTTP/1.0 %s\r\n\r\n' % status)
        self._transport.close()

    def data_received(self, data):
        self._data.extend(data)
        if self._state == 'INIT' and b'\r\n' in self._data:
            first_line, self._data = self._data.split(b'\r\n', 1)
            verb, uri, version = first_line.split()
            if verb != b'POST':
                self.write_status(b'405 Not Allowed')
                return
            self._state = 'HEADERS'
            self._subscriber_id = uri[1:]

        if self._state == 'HEADERS' and b'\r\n\r\n' in self._data:
            headers, self._data = self._data.split(b'\r\n\r\n', 1)
            headers = Message(io.BytesIO(headers))
            length = headers.get(b'content-length')
            if not length:
                self.write_status(b'400 Bad Request')
                return
            self._length = int(length)
            self._state = 'BODY'

        if self._state == 'BODY':
            if len(self._data) >= self._length:
                if self._subscriber_id:
                    self._factory.send_data(bytes(self._data),
                                            str(self._subscriber_id))
                    self.write_status(b'200 OK')
                else:
                    self.write_status(b'400 Bad Request')

    def connection_lost(self, exc):
        self._data = self._subscriber_id = None
        self._length = 0

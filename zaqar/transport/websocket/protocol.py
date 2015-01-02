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

import json

from zaqar.api.v1_1 import request as schema_validator
from zaqar.common.api import request
from zaqar.common.api import response
from zaqar.common import errors
import zaqar.openstack.common.log as logging

LOG = logging.getLogger(__name__)


class MessagingProtocol(websocket.WebSocketServerProtocol):

    def __init__(self, handler):
        websocket.WebSocketServerProtocol.__init__(self)
        self._handler = handler

    def onConnect(self, request):
        print("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        print("WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        if isBinary:
            # TODO(vkmc): Binary support will be added in the next cycle
            # For now, we are returning an invalid request response
            print("Binary message received: {0} bytes".format(len(payload)))
            req = self._dummy_request()
            body = {'error': 'Schema validation failed.'}
            headers = {'status': 400}
            resp = response.Response(req, body, headers)
            return resp
        else:
            try:
                print("Text message received: {0}".
                      format(payload.decode('utf8')))
                pl = json.loads(payload)
                req = self._create_request(pl)
                resp = (self._validate_request(pl, req) or
                        self._handler.process_request(req))
            except ValueError as ex:
                LOG.exception(ex)
                req = self._dummy_request()
                body = {'error': str(ex)}
                headers = {'status': 400}
                resp = response.Response(req, body, headers)
                return resp

        resp_json = json.dumps(resp.get_response())
        self.sendMessage(resp_json, isBinary)

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))

    @staticmethod
    def _create_request(pl):
        action = pl.get('action')
        body = pl.get('body', {})
        headers = pl.get('headers')

        return request.Request(action=action, body=body,
                               headers=headers, api="v1.1")

    @staticmethod
    def _validate_request(pl, req):
        try:
            action = pl.get('action')
            validator = schema_validator.RequestSchema()
            is_valid = validator.validate(action=action, body=pl)
        except errors.InvalidAction as ex:
            body = {'error': str(ex)}
            headers = {'status': 400}
            resp = response.Response(req, body, headers)
            return resp
        else:
            if not is_valid:
                body = {'error': 'Schema validation failed.'}
                headers = {'status': 400}
                resp = response.Response(req, body, headers)
                return resp

            return None

    @staticmethod
    def _dummy_request():
        action = 'None'
        return request.Request(action)
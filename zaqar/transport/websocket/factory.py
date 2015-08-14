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

from zaqar.transport.websocket import protocol


class ProtocolFactory(websocket.WebSocketServerFactory):

    protocol = protocol.MessagingProtocol

    def __init__(self, uri, debug, handler, external_port, auth_strategy,
                 loop):
        websocket.WebSocketServerFactory.__init__(
            self, url=uri, debug=debug, externalPort=external_port)
        self._handler = handler
        self._auth_strategy = auth_strategy
        self._loop = loop

    def __call__(self):
        proto = self.protocol(self._handler, self._auth_strategy, self._loop)
        proto.factory = self
        return proto

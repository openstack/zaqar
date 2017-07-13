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

import json

from autobahn.asyncio import websocket
import msgpack
from oslo_utils import uuidutils

from zaqar.transport.websocket import protocol


class ProtocolFactory(websocket.WebSocketServerFactory):

    protocol = protocol.MessagingProtocol

    def __init__(self, uri, handler, external_port, auth_strategy,
                 loop, secret_key):
        websocket.WebSocketServerFactory.__init__(
            self, url=uri, externalPort=external_port)
        self._handler = handler
        self._auth_strategy = auth_strategy
        self._loop = loop
        self._secret_key = secret_key
        self._protos = {}

    def __call__(self):
        proto_id = uuidutils.generate_uuid()
        proto = self.protocol(self._handler, proto_id, self._auth_strategy,
                              self._loop)
        self._protos[proto_id] = proto
        proto.factory = self
        return proto

    def unregister(self, proto_id):
        self._protos.pop(proto_id)


class NotificationFactory(object):

    protocol = protocol.NotificationProtocol

    def __init__(self, factory):
        self.message_factory = factory

    def set_subscription_url(self, url):
        self._subscription_url = url

    def get_subscriber(self, protocol):
        return '%s%s' % (self._subscription_url, protocol.proto_id)

    def send_data(self, data, proto_id):
        instance = self.message_factory._protos.get(proto_id)
        if instance:
            # NOTE(Eva-i): incoming data is encoded in JSON, let's convert it
            # to MsgPack, if notification should be encoded in binary format.
            if instance.notify_in_binary:
                data = msgpack.packb(json.loads(data))
            instance.sendMessage(data, instance.notify_in_binary)

    def __call__(self):
        return self.protocol(self)

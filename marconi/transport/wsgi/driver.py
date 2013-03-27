# Copyright (c) 2013 Rackspace, Inc.
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

import falcon

from marconi.common import config
from marconi import transport


cfg = config.namespace('drivers:transport:wsgi').from_options(port=8888)


class Driver(transport.DriverBase):

    def __init__(self, queue_controller, message_controller,
                 claim_controller):

        queue_item = transport.wsgi.queues.ItemResource(queue_controller)

        msg_collection = transport.wsgi.messages.CollectionResource(
            message_controller)
        msg_item = transport.wsgi.messages.ItemResource(message_controller)

        claim_collection = transport.wsgi.claims.CollectionResource(
            claim_controller)
        claim_item = transport.wsgi.claims.ItemResource(claim_controller)

        self.app = api = falcon.API()
        api.add_route('/v1/{tenant_id}/queues/{queue_name}', queue_item)
        api.add_route('/v1/{tenant_id}/queues/{queue_name}'
                      '/messages', msg_collection)
        api.add_route('/v1/{tenant_id}/queues/{queue_name}'
                      '/messages/{message_id}', msg_item)
        api.add_route('/v1/{tenant_id}/queues/{queue_name}'
                      '/claims', claim_collection)
        api.add_route('/v1/{tenant_id}/queues/{queue_name}'
                      '/claims/{claim_id}', claim_item)

    def listen(self):
        raise NotImplementedError

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
from wsgiref import simple_server

from marconi.common import config
import marconi.openstack.common.log as logging
from marconi import transport
from marconi.transport import auth
from marconi.transport.wsgi import claims
from marconi.transport.wsgi import messages
from marconi.transport.wsgi import queues
from marconi.transport.wsgi import stats

OPTIONS = {
    'bind': '0.0.0.0',
    'port': 8888
}

PROJECT_CFG = config.project('marconi')
GLOBAL_CFG = PROJECT_CFG.from_options()
WSGI_CFG = config.namespace('drivers:transport:wsgi').from_options(**OPTIONS)

LOG = logging.getLogger(__name__)


class Driver(transport.DriverBase):

    def __init__(self, storage):
        super(Driver, self).__init__(storage)

        self.app = falcon.API()

        queue_controller = self.storage.queue_controller
        message_controller = self.storage.message_controller
        claim_controller = self.storage.claim_controller

        # Queues Endpoints
        queue_collection = queues.CollectionResource(queue_controller)
        self.app.add_route('/v1/{project_id}/queues', queue_collection)

        queue_item = queues.ItemResource(queue_controller, message_controller)
        self.app.add_route('/v1/{project_id}/queues/{queue_name}', queue_item)

        stats_endpoint = stats.Resource(queue_controller)
        self.app.add_route('/v1/{project_id}/queues/{queue_name}'
                           '/stats', stats_endpoint)

        # Messages Endpoints
        msg_collection = messages.CollectionResource(message_controller)
        self.app.add_route('/v1/{project_id}/queues/{queue_name}'
                           '/messages', msg_collection)

        msg_item = messages.ItemResource(message_controller)
        self.app.add_route('/v1/{project_id}/queues/{queue_name}'
                           '/messages/{message_id}', msg_item)

        # Claims Endpoints
        claim_collection = claims.CollectionResource(claim_controller)
        self.app.add_route('/v1/{project_id}/queues/{queue_name}'
                           '/claims', claim_collection)

        claim_item = claims.ItemResource(claim_controller)
        self.app.add_route('/v1/{project_id}/queues/{queue_name}'
                           '/claims/{claim_id}', claim_item)

        # NOTE(flaper87): Install Auth
        if GLOBAL_CFG.auth_strategy:
            strategy = auth.strategy(GLOBAL_CFG.auth_strategy)
            self.app = strategy.install(self.app, PROJECT_CFG.conf)

    def listen(self):
        msg = _('Serving on host %(bind)s:%(port)s')
        msg %= {'bind': WSGI_CFG.bind, 'port': WSGI_CFG.port}
        LOG.debug(msg)
        httpd = simple_server.make_server(WSGI_CFG.bind, WSGI_CFG.port,
                                          self.app)
        httpd.serve_forever()

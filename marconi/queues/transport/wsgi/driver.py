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

import functools
from wsgiref import simple_server

import falcon
from oslo.config import cfg

from marconi.common.transport.wsgi import helpers
import marconi.openstack.common.log as logging
from marconi.queues import transport
from marconi.queues.transport import auth
from marconi.queues.transport import validation
from marconi.queues.transport.wsgi import claims
from marconi.queues.transport.wsgi import health
from marconi.queues.transport.wsgi import messages
from marconi.queues.transport.wsgi import metadata
from marconi.queues.transport.wsgi import queues
from marconi.queues.transport.wsgi import stats
from marconi.queues.transport.wsgi import v1

_WSGI_OPTIONS = [
    cfg.StrOpt('bind', default='127.0.0.1',
               help='Address on which the self-hosting server will listen'),

    cfg.IntOpt('port', default=8888,
               help='Port on which the self-hosting server will listen'),

    cfg.IntOpt('content_max_length', default=256 * 1024),
    cfg.IntOpt('metadata_max_length', default=64 * 1024)
]

_WSGI_GROUP = 'queues:drivers:transport:wsgi'

LOG = logging.getLogger(__name__)


class Driver(transport.DriverBase):

    def __init__(self, conf, storage):
        super(Driver, self).__init__(conf, storage)

        self._conf.register_opts(_WSGI_OPTIONS, group=_WSGI_GROUP)
        self._wsgi_conf = self._conf[_WSGI_GROUP]
        self._validate = validation.Validator(self._conf)

        self._init_routes()
        self._init_middleware()

    def _init_routes(self):
        """Initialize hooks and URI routes to resources."""
        before_hooks = [
            helpers.require_accepts_json,
            helpers.extract_project_id,

            # NOTE(kgriffs): Depends on project_id being extracted, above
            functools.partial(helpers.validate_queue_name,
                              self._validate.queue_name)
        ]

        self.app = falcon.API(before=before_hooks)

        queue_controller = self._storage.queue_controller
        message_controller = self._storage.message_controller
        claim_controller = self._storage.claim_controller

        # Home
        self.app.add_route('/v1', v1.V1Resource())

        # Queues Endpoints
        queue_collection = queues.CollectionResource(self._validate,
                                                     queue_controller)
        self.app.add_route('/v1/queues', queue_collection)

        queue_item = queues.ItemResource(queue_controller, message_controller)
        self.app.add_route('/v1/queues/{queue_name}', queue_item)

        stats_endpoint = stats.Resource(queue_controller)
        self.app.add_route('/v1/queues/{queue_name}'
                           '/stats', stats_endpoint)

        # Metadata Endpoints
        metadata_endpoint = metadata.Resource(self._wsgi_conf, self._validate,
                                              queue_controller)
        self.app.add_route('/v1/queues/{queue_name}'
                           '/metadata', metadata_endpoint)

        # Messages Endpoints
        msg_collection = messages.CollectionResource(self._wsgi_conf,
                                                     self._validate,
                                                     message_controller)
        self.app.add_route('/v1/queues/{queue_name}'
                           '/messages', msg_collection)

        msg_item = messages.ItemResource(message_controller)
        self.app.add_route('/v1/queues/{queue_name}'
                           '/messages/{message_id}', msg_item)

        # Claims Endpoints
        claim_collection = claims.CollectionResource(self._wsgi_conf,
                                                     self._validate,
                                                     claim_controller)
        self.app.add_route('/v1/queues/{queue_name}'
                           '/claims', claim_collection)

        claim_item = claims.ItemResource(self._wsgi_conf, self._validate,
                                         claim_controller)
        self.app.add_route('/v1/queues/{queue_name}'
                           '/claims/{claim_id}', claim_item)

        # Health
        self.app.add_route('/v1/health', health.HealthResource())

    def _init_middleware(self):
        """Initialize WSGI middlewarez."""

        # NOTE(flaper87): Install Auth
        if self._conf.auth_strategy:
            strategy = auth.strategy(self._conf.auth_strategy)
            self.app = strategy.install(self.app, self._conf)

    def listen(self):
        """Self-host using 'bind' and 'port' from the WSGI config group."""

        msg = _(u'Serving on host %(bind)s:%(port)s')
        msg %= {'bind': self._wsgi_conf.bind, 'port': self._wsgi_conf.port}
        LOG.info(msg)

        httpd = simple_server.make_server(self._wsgi_conf.bind,
                                          self._wsgi_conf.port,
                                          self.app)
        httpd.serve_forever()

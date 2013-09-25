# Copyright (c) 2013 Rackspace Hosting, Inc.
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
"""marconi-proxy: maintains a mapping from inserted queues to partitions

Supports the following operator API:
- [GET] /v1/partitions - lists registered partitions
- [PUT|GET|DELETE] /v1/partitions/{partition}
- [GET] /v1/catalogue

Running:
- configure marconi.conf appropriately
- gunicorn marconi.proxy.transport.wsgi.app:app
"""
from wsgiref import simple_server

import falcon

from marconi.common import config
import marconi.openstack.common.log as logging
from marconi.proxy import transport
from marconi.proxy.transport.wsgi import (
    catalogue, forward, health, metadata,
    partitions, queues, v1, version
)
from marconi.proxy.utils import round_robin
from marconi.queues.transport import auth


_VER = version.path()

OPTIONS = {
    'bind': '0.0.0.0',
    'port': 8889
}

PROJECT_CFG = config.project('marconi', 'marconi-proxy')
GLOBAL_CFG = PROJECT_CFG.from_options()
WSGI_CFG = config.namespace('proxy:drivers:transport:wsgi').from_options(
    **OPTIONS
)

LOG = logging.getLogger(__name__)


# TODO(cpp-cabrera): refactor to avoid duplication with queues..wsgi
def _check_media_type(req, resp, params):
    if not req.client_accepts('application/json'):
        raise falcon.HTTPNotAcceptable(
            u'''
Endpoint only serves `application/json`; specify client-side
media type support with the "Accept" header.''',
            href=u'http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html',
            href_text=u'14.1 Accept, Hypertext Transfer Protocol -- HTTP/1.1')


class Driver(transport.DriverBase):
    """Entry point to the proxy

    :param storage: storage driver to use
    :param cache: cache driver to use
    """
    def __init__(self, storage, cache):
        super(Driver, self).__init__(storage, cache)
        self.app = None
        self._catalogue = self.storage.catalogue_controller
        self._partitions = self.storage.partitions_controller
        self._selector = round_robin.Selector()

        self._init_routes()
        self._init_middleware()

    def _init_routes(self):
        self.app = falcon.API(before=[_check_media_type])

        # NOTE(cpp-cabrera): proxy-specififc routes
        self.app.add_route(_VER + '/partitions',
                           partitions.Listing(self._partitions))
        self.app.add_route(_VER + '/partitions/{partition}',
                           partitions.Resource(self._partitions))
        self.app.add_route(_VER + '/catalogue',
                           catalogue.Listing(self._catalogue))
        self.app.add_route(_VER + '/catalogue/{queue}',
                           catalogue.Resource(self._catalogue))
        self.app.add_route(_VER + '/health',
                           health.Resource())

        # NOTE(cpp-cabrera): queue handling routes
        self.app.add_route(_VER + '/queues',
                           queues.Listing(self._catalogue))
        self.app.add_route(_VER + '/queues/{queue}',
                           queues.Resource(self._partitions,
                                           self._catalogue,
                                           self.cache, self._selector))

        # NOTE(cpp-cabrera): Marconi forwarded routes
        self.app.add_route(_VER,
                           v1.Resource(self._partitions))

        # NOTE(cpp-cabrera): Marconi forwarded routes involving a queue
        self.app.add_route(_VER + '/queues/{queue}/claims',
                           forward.ClaimCreate(self._partitions,
                                               self._catalogue,
                                               self.cache,
                                               self._selector))

        self.app.add_route(_VER + '/queues/{queue}/claims/{cid}',
                           forward.Claim(self._partitions,
                                         self._catalogue,
                                         self.cache, self._selector))

        self.app.add_route(_VER + '/queues/{queue}/messages',
                           forward.MessageBulk(self._partitions,
                                               self._catalogue,
                                               self.cache,
                                               self._selector))

        self.app.add_route(_VER + '/queues/{queue}/messages/{mid}',
                           forward.Message(self._partitions,
                                           self._catalogue, self.cache,
                                           self._selector))

        self.app.add_route(_VER + '/queues/{queue}/stats',
                           forward.Stats(self._partitions,
                                         self._catalogue,
                                         self.cache, self._selector))

        self.app.add_route(_VER + '/queues/{queue}/metadata',
                           metadata.Resource(self._partitions,
                                             self._catalogue,
                                             self.cache, self._selector))

    # TODO(cpp-cabrera): refactor to avoid duplication with queues..wsgi
    def _init_middleware(self):
        """Initialize WSGI middlewarez."""

        # NOTE(flaper87): Install Auth
        if GLOBAL_CFG.auth_strategy:
            strategy = auth.strategy(GLOBAL_CFG.auth_strategy)
            self.app = strategy.install(self.app, PROJECT_CFG.conf)

    def listen(self):
        """Listens on the 'bind:port' as per the config."""

        msg = _(u'Serving on host {bind}:{port}').format(
            bind=WSGI_CFG.bind, port=WSGI_CFG.port
        )
        LOG.info(msg)

        httpd = simple_server.make_server(WSGI_CFG.bind, WSGI_CFG.port,
                                          self.app)
        httpd.serve_forever()

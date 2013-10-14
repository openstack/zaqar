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

"""marconi-proxy (base): Interface for driver implementations."""

import abc
from wsgiref import simple_server

import falcon
from oslo.config import cfg
import six

from marconi.common.transport.wsgi import helpers
import marconi.openstack.common.log as logging
from marconi.proxy import transport
from marconi.proxy.transport.wsgi import version
from marconi.proxy.utils import round_robin
from marconi.queues.transport import auth


_WSGI_OPTIONS = [
    cfg.StrOpt('bind', default='0.0.0.0',
               help='Address to bind this server to'),

    cfg.IntOpt('port', default=8888,
               help='Port to bind this server to'),

]

cfg.CONF.register_opt(cfg.StrOpt('auth_strategy', default=''))
cfg.CONF.register_opts(_WSGI_OPTIONS,
                       group='proxy:drivers:transport:wsgi')

GLOBAL_CFG = cfg.CONF
WSGI_CFG = cfg.CONF['proxy:drivers:transport:wsgi']

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class DriverBase(transport.DriverBase):
    """Entry point to the proxy

    :param storage: storage driver to use
    :type storage: marconi.proxy.storage.base.DriverBase
    :param cache: cache driver to use
    :type cache: marconi.common.cache.backends.BaseCache
    """
    def __init__(self, storage, cache):
        super(DriverBase, self).__init__(storage, cache)
        self.app = None
        self.catalogue = self.storage.catalogue_controller
        self.partitions = self.storage.partitions_controller
        self.selector = round_robin.Selector()

        self._init_routes()
        self._init_middleware()

    def _init_routes(self):
        version_path = version.path()
        self.app = falcon.API(before=[helpers.require_accepts_json])
        for route, resource in self.bridge:
            self.app.add_route(version_path + route, resource)

    # TODO(cpp-cabrera): refactor to avoid duplication with queues..wsgi
    def _init_middleware(self):
        """Initialize WSGI middlewarez."""

        # NOTE(flaper87): Install Auth
        if GLOBAL_CFG.auth_strategy:
            strategy = auth.strategy(GLOBAL_CFG.auth_strategy)
            self.app = strategy.install(self.app, GLOBAL_CFG)

    @abc.abstractproperty
    def bridge(self):
        """Constructs a list of route/responder pairs that can be used to
        establish the functionality of this driver.

        Note: the routes should be unversioned.

        :rtype: [(str, falcon-compatible responser)]
        """
        raise NotImplementedError

    def listen(self):
        """Listens on the 'bind:port' as per the config."""

        msg = _(u'Serving on host {bind}:{port}').format(
            bind=WSGI_CFG.bind, port=WSGI_CFG.port
        )
        LOG.info(msg)

        httpd = simple_server.make_server(WSGI_CFG.bind, WSGI_CFG.port,
                                          self.app)
        httpd.serve_forever()

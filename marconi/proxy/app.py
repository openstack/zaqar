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
"""marconi-proxy: maintains a mapping from inserted queues to partitions.

Supports the following operator API:
- [GET] /v1/partitions - lists registered partitions
- [PUT|GET|DELETE] /v1/partitions/{partition}
- [GET] /v1/catalogue

Running:
- configure marconi.conf appropriately
- gunicorn marconi.proxy.app:app
"""
import falcon
from oslo.config import cfg
from stevedore import driver

from marconi.common.cache import cache
from marconi.common import config
from marconi.common import exceptions

from marconi.proxy.resources import catalogue
from marconi.proxy.resources import forward
from marconi.proxy.resources import health
from marconi.proxy.resources import metadata
from marconi.proxy.resources import partitions
from marconi.proxy.resources import queues
from marconi.proxy.resources import v1
from marconi.proxy.utils import round_robin


# TODO(cpp-cabrera): wrap all this up in a nice bootstrap.py
# TODO(cpp-cabrera): mirror marconi.queues.transport with this
#                    for nicer deployments (and eventual
#                    proxy multi-transport support!)
PROJECT_CFG = config.project('marconi')
CFG = config.namespace('drivers:proxy').from_options(
    transport='wsgi',
    storage='memory')

# TODO(cpp-cabrera): need to wrap this in a bootstrap class to defer
#                    loading of config until it is run in a WSGI
#                    context, otherwise, it breaks the test suite.
if __name__ == '__main__':
    PROJECT_CFG.load()

app = falcon.API()

try:
    storage = driver.DriverManager('marconi.proxy.storage',
                                   CFG.storage,
                                   invoke_on_load=True)
except RuntimeError as exc:
    raise exceptions.InvalidDriver(exc)

catalogue_driver = storage.driver.catalogue_controller
partitions_driver = storage.driver.partitions_controller
cache_driver = cache.get_cache(cfg.CONF)
selector = round_robin.Selector()


# TODO(cpp-cabrera): don't encode API version in routes -
#                    let's handle this elsewhere
# NOTE(cpp-cabrera): Proxy-specific routes
app.add_route('/v1/partitions',
              partitions.Listing(partitions_driver))
app.add_route('/v1/partitions/{partition}',
              partitions.Resource(partitions_driver))
app.add_route('/v1/catalogue',
              catalogue.Listing(catalogue_driver))
app.add_route('/v1/catalogue/{queue}',
              catalogue.Resource(catalogue_driver))
app.add_route('/v1/health',
              health.Resource())

# NOTE(cpp-cabrera): queue handling routes
app.add_route('/v1/queues',
              queues.Listing(catalogue_driver))
app.add_route('/v1/queues/{queue}',
              queues.Resource(partitions_driver, catalogue_driver,
                              cache_driver, selector))

# NOTE(cpp-cabrera): Marconi forwarded routes
app.add_route('/v1',
              v1.Resource(partitions_driver))

# NOTE(cpp-cabrera): Marconi forwarded routes involving a queue
app.add_route('/v1/queues/{queue}/claims',
              forward.ClaimCreate(partitions_driver,
                                  catalogue_driver,
                                  cache_driver, selector))

app.add_route('/v1/queues/{queue}/claims/{cid}',
              forward.Claim(partitions_driver,
                            catalogue_driver,
                            cache_driver, selector))

app.add_route('/v1/queues/{queue}/messages',
              forward.MessageBulk(partitions_driver,
                                  catalogue_driver,
                                  cache_driver, selector))

app.add_route('/v1/queues/{queue}/messages/{mid}',
              forward.Message(partitions_driver,
                              catalogue_driver, cache_driver, selector))

app.add_route('/v1/queues/{queue}/stats',
              forward.Stats(partitions_driver,
                            catalogue_driver,
                            cache_driver, selector))

app.add_route('/v1/queues/{queue}/metadata',
              metadata.Resource(partitions_driver,
                                catalogue_driver,
                                cache_driver, selector))

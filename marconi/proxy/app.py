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

Deploy requirements:
- redis-server, default port
- gunicorn
- python >= 2.7
- falcon
- msgpack
- requests

Running:
- gunicorn marconi.proxy.app:app
"""
import falcon
import redis

from marconi.proxy.resources import catalogue
from marconi.proxy.resources import health
from marconi.proxy.resources import partitions
from marconi.proxy.resources import queues
from marconi.proxy.resources import v1

app = falcon.API()
client = redis.StrictRedis()

# TODO(cpp-cabrera): don't encode API version in routes -
#                    let's handle this elsewhere
# NOTE(cpp-cabrera): Proxy-specific routes
app.add_route('/v1/partitions',
              partitions.Listing(client))
app.add_route('/v1/partitions/{partition}',
              partitions.Resource(client))
app.add_route('/v1/catalogue',
              catalogue.Listing(client))
app.add_route('/v1/catalogue/{queue}',
              catalogue.Resource(client))

# NOTE(cpp-cabrera): queue handling routes
app.add_route('/v1/queues',
              queues.Listing(client))
app.add_route('/v1/queues/{queue}',
              queues.Resource(client))

# NOTE(cpp-cabrera): Marconi forwarded routes
app.add_route('/v1',
              v1.Resource(client))
app.add_route('/v1/health',
              health.Resource(client))

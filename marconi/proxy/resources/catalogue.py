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
"""catalogue: maintains a directory of all queues proxied through the system

Storage maintains an entry for each queue as follows:

{
  q.{project}.{queue}: {'h': ByteString, 'n': ByteString, 'm': MsgPack}
}

"m" -> metadata
"n" -> name
"h" -> HTTP host

A list of all queues is also stored as:

{
  qs.{project}: [{name}, {name}, {name}]
}
"""
import json

import falcon
import msgpack

from marconi.proxy.utils import helpers


class Listing(object):
    """A listing of all entries in the catalogue."""
    def __init__(self, client):
        self.client = client

    def on_get(self, request, response):
        project = helpers.get_project(request)
        key = 'qs.%s' % project
        if not self.client.exists(key):
            response.status = falcon.HTTP_204
            return

        resp = {}
        for q in self.client.lrange(key, 0, -1):
            hkey = 'q.%s.%s' % (project, q.decode('utf8'))
            queue = q.decode('utf8')
            h, n, m = self.client.hmget(hkey, ['h', 'n', 'm'])
            if not all([h, n]):
                continue

            resp[queue] = {
                'host': h.decode('utf8'),
                'name': n.decode('utf8')
            }
            resp[queue]['metadata'] = msgpack.loads(m) if m else {}

        if not resp:
            response.status = falcon.HTTP_204
            return

        response.status = falcon.HTTP_200
        response.body = json.dumps(resp, ensure_ascii=False)


class Resource(object):
    """A single catalogue entry."""
    def __init__(self, client):
        self.client = client

    def on_get(self, request, response, queue):
        key = 'q.%s.%s' % (helpers.get_project(request), queue)
        if not self.client.exists(key):
            raise falcon.HTTPNotFound()
        h, n, m = self.client.hmget(key, ['h', 'n', 'm'])
        resp = {
            'name': n.decode('utf8'),
            'host': h.decode('utf8'),
        }
        resp['metadata'] = msgpack.loads(m) if m else {}

        response.status = falcon.HTTP_200
        response.body = json.dumps(resp, ensure_ascii=False)

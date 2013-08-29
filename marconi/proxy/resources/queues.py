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
"""queues: routing and cataloguing queue operations on marconi

The queues resource performs routing to a marconi partition for
requests targeting queues.

For the case of a queue listing, the prooxy handles the request in its
entirety, since queues for a given project may be spread across
multiple partitions. This requires the proxy catalogue being
consistent with the state of the entire deployment.

For the case of accessing a particular queue, the catalogue is updated
based on the operation. A DELETE removes entries from the catalogue. A
PUT adds an entry to the catalogue. A GET asks marconi for an
authoritative response.
"""
import collections
import json

import falcon
import msgpack
import requests

from marconi.proxy.utils import helpers
from marconi.proxy.utils import http
from marconi.proxy.utils import node


class Listing(object):
    """Responsible for constructing a valid marconi queue listing
    from the content stored in the catalogue.
    """
    def __init__(self, client):
        self.client = client

    def on_get(self, request, response):
        project = helpers.get_project(request)
        key = 'qs.%s' % project
        if not self.client.exists(key):
            response.status = falcon.HTTP_204
            return

        kwargs = {}
        request.get_param('marker', store=kwargs)
        request.get_param_as_int('limit', store=kwargs)
        request.get_param_as_bool('detailed', store=kwargs)

        resp = collections.defaultdict(list)
        for q in sorted(self.client.lrange(key, 0, -1)):
            queue = q.decode('utf8')
            if queue < kwargs.get('marker', 0):
                continue
            entry = {
                'href': request.path + '/' + queue,
                'name': queue
            }
            if kwargs.get('detailed', None):
                qkey = 'q.%s.%s' % (project, queue)
                data = self.client.hget(qkey, 'm')
                metadata = msgpack.loads(data)
                entry['metadata'] = metadata
            resp['queues'].append(entry)
            kwargs['marker'] = queue
            if len(resp['queues']) == kwargs.get('limit', None):
                break

        if not resp:
            response.status = falcon.HTTP_204
            return

        resp['links'].append({
            'rel': 'next',
            'href': request.path + falcon.to_query_str(kwargs)
        })

        response.content_location = request.relative_uri
        response.body = json.dumps(resp, ensure_ascii=False)


class Resource(object):
    def __init__(self, client):
        self.client = client

    def _make_key(self, request, queue):
        project = helpers.get_project(request)
        return 'q.%s.%s' % (project, queue)

    def on_get(self, request, response, queue):
        key = self._make_key(request, queue)
        if not self.client.exists(key):
            raise falcon.HTTPNotFound()

        h, n = self.client.hmget(key, ['h', 'n'])
        if not (h and n):
            raise falcon.HTTPNotFound()

        resp = helpers.forward(self.client, request, queue)
        response.set_headers(resp.headers)
        response.status = http.status(resp.status_code)
        response.body = resp.content

    def on_put(self, request, response, queue):
        key = self._make_key(request, queue)
        project = helpers.get_project(request)
        if self.client.exists(key):
            response.status = falcon.HTTP_204
            return

        partition = node.weighted_select(self.client)
        host = node.round_robin(self.client, partition)
        url = '{host}/v1/queues/{queue}'.format(host=host, queue=queue)
        resp = requests.put(url, headers=request._headers)

        # NOTE(cpp-cabrera): only catalogue a queue if a request is good
        if resp.ok:
            self.client.hmset(key, {
                'h': host,
                'n': queue
            })
            self.client.rpush('qs.%s' % project, queue)

        response.status = http.status(resp.status_code)
        response.body = resp.content

    def on_delete(self, request, response, queue):
        key = self._make_key(request, queue)

        project = helpers.get_project(request)
        resp = helpers.forward(self.client, request, queue)
        response.set_headers(resp.headers)
        response.status = http.status(resp.status_code)

        # avoid deleting a queue if the request is bad
        if not resp.ok:
            self.client.hdel(key, queue)
            self.client.lrem('qs.%s' % project, 1, queue)

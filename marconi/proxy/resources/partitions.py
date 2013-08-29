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
"""partitions: a registry of all marconi partitions this proxy can route to

A partition is added by an operator by interacting with the
partition-related endpoints. When specifying a partition, the
following fields are required:

{
    "name": String,
    "weight": Integer,
    "nodes": [HTTP_EndPoints(:Port), ...]
}

In storage, a partition entry looks like:

{
    "p.{name}": {"n": ByteString, "w": ByteString, "n": MsgPack}
}

Storage also maintains a list of partitions as:
{
    "ps": [{name}, {name}, {name}, ...]
}
"""
import json

import falcon
import msgpack


class Listing(object):
    """A listing of all partitions registered."""
    def __init__(self, client):
        self.client = client

    def on_get(self, request, response):
        partitions = self.client.lrange('ps', 0, -1)
        resp = {}
        for p in partitions:
            key = 'p.%s' % p.decode('utf8')
            n, w = self.client.hmget(key, ['n', 'w'])
            if not all([n, w]):
                continue
            resp[p.decode('utf8')] = {'weight': int(w),
                                      'nodes': [node.decode('utf8') for node
                                                in msgpack.loads(n)]}

        if not resp:
            response.status = falcon.HTTP_204
            return

        response.body = json.dumps(resp, ensure_ascii=False)
        response.status = falcon.HTTP_200


class Resource(object):
    """A means to interact with individual partitions."""
    def __init__(self, client):
        self.client = client

    def on_get(self, request, response, partition):
        n, w = self.client.hmget('p.%s' % partition, ['n', 'w'])

        if not all([n, w]):  # ensure all the data was returned correctly
            raise falcon.HTTPNotFound()

        nodes, weight = msgpack.loads(n), int(w)
        response.body = json.dumps({
            'nodes': [node.decode('utf8') for node in nodes],
            'weight': weight,
        }, ensure_ascii=False)

    def _validate_put(self, data):
        if not isinstance(data, dict):
            raise falcon.HTTPBadRequest(
                'Invalid metadata', 'Define a partition as a dict'
            )

        if 'nodes' not in data:
            raise falcon.HTTPBadRequest(
                'Missing nodes list', 'Provide a list of nodes'
            )

        if not data['nodes']:
            raise falcon.HTTPBadRequest(
                'Empty nodes list', 'Nodes list cannot be empty'
            )

        if not isinstance(data['nodes'], list):
            raise falcon.HTTPBadRequest(
                'Invalid nodes', 'Nodes must be a list of URLs'
            )

        # TODO(cpp-cabrera): check [str]

        if 'weight' not in data:
            raise falcon.HTTPBadRequest(
                'Missing weight',
                'Provide an integer weight for this partition'
            )

        if not isinstance(data['weight'], int):
            raise falcon.HTTPBadRequest(
                'Invalid weight', 'Weight must be an integer'
            )

    def on_put(self, request, response, partition):
        if partition.startswith('_'):
            raise falcon.HTTPBadRequest(
                'Reserved name', '_names are reserved for internal use'
            )

        key = 'p.%s' % partition
        if self.client.exists(key):
            response.status = falcon.HTTP_204
            return

        try:
            data = json.loads(request.stream.read().decode('utf8'))
        except ValueError:
            raise falcon.HTTPBadRequest(
                'Invalid JSON', 'This is not a valid JSON stream.'
            )

        self._validate_put(data)
        self.client.hmset(key, {'n': msgpack.dumps(data['nodes']),
                                'w': data['weight'],
                                'c': 0})
        self.client.rpush('ps', partition)
        response.status = falcon.HTTP_201

    def on_delete(self, request, response, partition):
        self.client.delete('p.%s' % partition)
        self.client.lrem('ps', 1, partition)
        response.status = falcon.HTTP_204

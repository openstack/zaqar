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
    "hosts": [HTTP_EndPoints(:Port), ...]
}
"""
import json

import falcon

from marconi.proxy.storage import exceptions


class Listing(object):
    """A listing of all partitions registered."""
    def __init__(self, partitions_controller):
        self._ctrl = partitions_controller

    def on_get(self, request, response):
        """Returns a partition listing as a JSON object:

        {
            "name": {"weight": 100, "hosts": [""]},
            "..."
        }

        :returns: HTTP | [200, 204]
        """
        resp = {}
        for p in self._ctrl.list():
            resp[p['name']] = {'weight': int(p['weight']),
                               'hosts': p['hosts']}

        if not resp:
            response.status = falcon.HTTP_204
            return

        response.body = json.dumps(resp, ensure_ascii=False)
        response.status = falcon.HTTP_200


class Resource(object):
    """A means to interact with individual partitions."""
    def __init__(self, partitions_controller):
        self._ctrl = partitions_controller

    def on_get(self, request, response, partition):
        """Returns a JSON object for a single partition entry:

        {"weight": 100, "hosts": [""]}

        :returns: HTTP | [200, 404]
        """
        data = None
        try:
            data = self._ctrl.get(partition)
        except exceptions.PartitionNotFound:
            raise falcon.HTTPNotFound()

        hosts, weight = data['hosts'], data['weight']
        response.body = json.dumps({
            'hosts': data['hosts'],
            'weight': data['weight'],
        }, ensure_ascii=False)

    def _validate_put(self, data):
        if not isinstance(data, dict):
            raise falcon.HTTPBadRequest(
                'Invalid metadata', 'Define a partition as a dict'
            )

        if 'hosts' not in data:
            raise falcon.HTTPBadRequest(
                'Missing hosts list', 'Provide a list of hosts'
            )

        if not data['hosts']:
            raise falcon.HTTPBadRequest(
                'Empty hosts list', 'Hosts list cannot be empty'
            )

        if not isinstance(data['hosts'], list):
            raise falcon.HTTPBadRequest(
                'Invalid hosts', 'Hosts must be a list of URLs'
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
        """Creates a new partition. Expects the following input:

        {"weight": 100, "hosts": [""]}

        :returns: HTTP | [201, 204]
        """
        if partition.startswith('_'):
            raise falcon.HTTPBadRequest(
                'Reserved name', '_names are reserved for internal use'
            )

        if self._ctrl.exists(partition):
            response.status = falcon.HTTP_204
            return

        try:
            data = json.loads(request.stream.read().decode('utf8'))
        except ValueError:
            raise falcon.HTTPBadRequest(
                'Invalid JSON', 'This is not a valid JSON stream.'
            )

        self._validate_put(data)
        self._ctrl.create(partition,
                          weight=data['weight'],
                          hosts=data['hosts'])
        response.status = falcon.HTTP_201

    def on_delete(self, request, response, partition):
        """Removes an existing partition.

        :returns: HTTP | 204
        """
        self._ctrl.delete(partition)
        response.status = falcon.HTTP_204

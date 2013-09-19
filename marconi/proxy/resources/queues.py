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

from marconi.proxy.storage import exceptions
from marconi.proxy.utils import helpers
from marconi.proxy.utils import http
from marconi.proxy.utils import node


class Listing(object):
    """Responsible for constructing a valid marconi queue listing
    from the content stored in the catalogue.
    """
    def __init__(self, catalogue_controller):
        self._catalogue = catalogue_controller

    #TODO(cpp-cabrera): consider revisiting this implementation
    #                   to use concurrent requests + merge/sort
    #                   for great impl./data DRYness
    def on_get(self, request, response):
        project = helpers.get_project(request)

        kwargs = {}
        request.get_param('marker', store=kwargs)
        request.get_param_as_int('limit', store=kwargs)
        request.get_param_as_bool('detailed', store=kwargs)

        resp = collections.defaultdict(list)
        for q in self._catalogue.list(project):
            queue = q['name']
            if queue < kwargs.get('marker', ''):
                continue
            entry = {
                'href': request.path + '/' + queue,
                'name': queue
            }
            if kwargs.get('detailed', None):
                entry['metadata'] = queue['metadata']
            resp['queues'].append(entry)
            kwargs['marker'] = queue
            if len(resp['queues']) == kwargs.get('limit', 0):
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
    def __init__(self, partitions_controller, catalogue_controller):
        self._partitions = partitions_controller
        self._catalogue = catalogue_controller

    def _rr(self, project, queue):
        """Returns the next host to use for a request."""
        partition = None
        try:
            partition = self._catalogue.get(project, queue)['partition']
        except exceptions.EntryNotFound:
            raise falcon.HTTPNotFound()

        return self._partitions.select(partition)

    def on_get(self, request, response, queue):
        project = helpers.get_project(request)
        host = self._rr(project, queue)
        resp = helpers.forward(host, request)

        response.set_headers(resp.headers)
        response.status = http.status(resp.status_code)
        response.body = resp.content

    def on_put(self, request, response, queue):
        project = helpers.get_project(request)
        if self._catalogue.exists(project, queue):
            response.status = falcon.HTTP_204
            return

        partition = node.weighted_select(self._partitions.list())
        if partition is None:
            raise falcon.HTTPBadRequest(
                "No partitions registered",
                "Register partitions before continuing"
            )
        host = partition['hosts'][0]
        resp = helpers.forward(host, request)

        # NOTE(cpp-cabrera): only catalogue a queue if a request is good
        if resp.ok:
            self._catalogue.insert(project, queue, partition['name'], host)

        response.status = http.status(resp.status_code)
        response.body = resp.content

    def on_delete(self, request, response, queue):
        project = helpers.get_project(request)
        host = self._rr(project, queue)
        resp = helpers.forward(host, request)

        # avoid deleting a queue if the request is bad
        if resp.ok:
            self._catalogue.delete(project, queue)

        response.set_headers(resp.headers)
        response.status = http.status(resp.status_code)

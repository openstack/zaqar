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

For the case of a queue listing, the proxy handles the request in its
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

from marconi.proxy.utils import (
    forward, lookup, helpers, http, partition
)


class Listing(object):
    """Responsible for constructing a valid marconi queue listing
    from the content stored in the catalogue

    :param catalogue_controller: storage driver to use
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
        for queue in self._catalogue.list(project):
            queue_name = queue['name']
            if queue_name < kwargs.get('marker', ''):
                continue
            entry = {
                'href': request.path + '/' + queue_name,
                'name': queue_name
            }
            if kwargs.get('detailed', None):
                entry['metadata'] = queue['metadata']
            resp['queues'].append(entry)
            kwargs['marker'] = queue_name
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


class Resource(forward.ForwardMixin):
    """Forwards queue requests to marconi queues API and updates the
    catalogue

    :param partitions_controller: partitions storage driver
    :param catalogue_conroller: catalogue storage driver
    :param cache: caching driver
    :param selector: algorithm to use to select next node
    :param methods: HTTP methods to automatically derive from mixin
    """
    def __init__(self, partitions_controller, catalogue_controller,
                 cache, selector):
        self._partitions = partitions_controller
        self._catalogue = catalogue_controller
        self._cache = cache
        super(Resource, self).__init__(partitions_controller,
                                       catalogue_controller,
                                       cache, selector,
                                       methods=['get', 'head'])

    def on_put(self, request, response, queue):
        """Create a queue in the catalogue, then forwards to marconi.

        This is the only time marconi proxy ever needs to select a
        partition for a queue. The association is created in the
        catalogue. This should also be the only time
        partition.weighted_select is ever called.

        :raises: HTTPInternalServerError - if no partitions are registered
        """
        project = helpers.get_project(request)

        # NOTE(cpp-cabrera): if we've already registered a queue,
        # don't try to create it again, because it will duplicate it
        # across partitions.
        #
        # There exists a race condition here, but it is benign. It's
        # possible that after the existence check has succeeded,
        # another request may succeed in DELETEing a queue. In this
        # scenario, the queue will be recreated on another partition,
        # which is reasonable, since the user meant to both DELETE and
        # PUT That queue.
        if lookup.exists(project, queue,
                         self._catalogue, self._cache):
            response.status = falcon.HTTP_204
            return

        target = partition.weighted_select(self._partitions.list())
        if target is None:
            raise falcon.HTTPInternalServerError(
                "No partitions registered",
                "Contact the system administrator for more details."
            )
        host = target['hosts'][0]
        resp = helpers.forward(host, request)

        # NOTE(cpp-cabrera): only catalogue a queue if it was created
        if resp.status_code == 201:
            self._catalogue.insert(project, queue, target['name'],
                                   host)

        response.set_headers(helpers.capitalized(resp.headers))
        response.status = http.status(resp.status_code)
        response.body = resp.content

    def on_delete(self, request, response, queue):
        project = helpers.get_project(request)
        resp = self.forward(request, response, queue)

        # avoid deleting a queue if the request is bad
        if resp.ok:
            self._catalogue.delete(project, queue)
            lookup.invalidate_entry(project, queue, self._cache)

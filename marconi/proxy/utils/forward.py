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

"""forward: exposes a mixin class appropriate for forwarding requests."""

import falcon

from marconi.openstack.common import log
from marconi.proxy.utils import helpers
from marconi.proxy.utils import http
from marconi.proxy.utils import lookup


LOG = log.getLogger(__name__)


class ForwardMixin(object):
    """Implements falcon-compatible forwarding for resources

    :param partitions_controller: talks to partitions storage
    :param catalogue_controller: talks to catalogue storage
    :param cache: localized, fast lookups
    :param selector: @see utils.round_robin - host selection order
    :param methods: [text] - allowed methods, e.g., ['get', 'post']
    """

    def __init__(self, partitions_controller, catalogue_controller,
                 cache, selector, methods):
        self._catalogue = catalogue_controller
        self._partitions = partitions_controller
        self._cache = cache
        self._selector = selector

        for method in methods:
            assert method.lower() in http.METHODS
            setattr(self, 'on_' + method.lower(), self.forward)

    def forward(self, request, response, queue, **kwargs):
        """Forwards requests in a selector-driven fashion."""
        project = helpers.get_project(request)
        LOG.debug('FORWARD - project/queue: {0}/{1}'.format(
            project, queue
        ))

        partition = lookup.partition(project, queue,
                                     self._catalogue,
                                     self._cache)

        # NOTE(cpp-cabrera): we tried to look up a catalogue
        # entry and it failed. This happens if the associated
        # queue doesn't exist under that project.
        if not partition:
            LOG.debug('Catalogue entry not found')
            raise falcon.HTTPNotFound()

        hosts = lookup.hosts(partition, self._partitions, self._cache)

        # NOTE(cpp-cabrera): we tried to look up a partition, and it
        # failed. This only happens if a partition is deleted from
        # the primary store between here and the last call.
        if not hosts:
            LOG.debug('Partition not found')
            raise falcon.HTTPNotFound()

        # round robin to choose the desired host
        host = self._selector.next(partition, hosts)

        # send the request, update the response
        resp = helpers.forward(host, request)

        # NOTE(zyuan): normalize the lower-case header from
        # `requests` to Caml-Case and forward the headers back
        response.set_headers(helpers.capitalized(resp.headers))
        response.status = http.status(resp.status_code)
        response.body = resp.content

        # NOTE(cpp-cabrera): in case responder must do more afterwards
        return resp

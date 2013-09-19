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
"""forward: a resource for each marconi route where the desired result
is to just pass along a request to marconi.
"""
import falcon

from marconi.proxy.storage import exceptions
from marconi.proxy.utils import helpers
from marconi.proxy.utils import http


class ForwardMixin(object):
    """Implements falcon-compatible forwarding for resources."""

    def __init__(self, partitions_controller, catalogue_controller,
                 methods):
        """Initializes a forwarding resource.

        :param partitions_controller: talks to partitions storage
        :param catalogue_controller: talks to catalogue storage
        :param methods: [str] - allowed methods, e.g., ['get', 'post']
        """
        self._catalogue = catalogue_controller
        self._partitions = partitions_controller
        for method in methods:
            setattr(self, 'on_' + method, self.forward)

    def forward(self, request, response, queue, **kwargs):
        project = helpers.get_project(request)

        # find the partition, round-robin the host
        partition = None
        try:
            partition = self._catalogue.get(project, queue)['partition']
        except exceptions.EntryNotFound:
            raise falcon.HTTPNotFound()
        host = self._partitions.select(partition)

        # send the request, update the response
        resp = helpers.forward(host, request)
        response.status = http.status(resp.status_code)
        response.body = resp.content


class ClaimCreate(ForwardMixin):
    """Handler for the endpoint to post claims."""
    def __init__(self, partitions_controller, catalogue_controller):
        super(ClaimCreate, self).__init__(
            partitions_controller, catalogue_controller,
            methods=['post'])


class Claim(ForwardMixin):
    """Handler for dealing with claims directly."""
    def __init__(self, partitions_controller, catalogue_controller):
        super(Claim, self).__init__(
            partitions_controller, catalogue_controller,
            methods=['patch', 'delete', 'get'])


class MessageBulk(ForwardMixin):
    """Handler for bulk message operations."""
    def __init__(self, partitions_controller, catalogue_controller):
        super(MessageBulk, self).__init__(
            partitions_controller, catalogue_controller,
            methods=['get', 'delete', 'post'])


class Message(ForwardMixin):
    """Handler for individual messages."""
    def __init__(self, partitions_controller, catalogue_controller):
        super(Message, self).__init__(
            partitions_controller, catalogue_controller,
            methods=['get', 'delete'])


class Stats(ForwardMixin):
    """Handler for forwarding queue stats requests."""
    def __init__(self, partitions_controller, catalogue_controller):
        super(Stats, self).__init__(
            partitions_controller, catalogue_controller,
            methods=['get'])

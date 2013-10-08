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

from marconi.proxy.utils import forward


class ClaimCreate(forward.ForwardMixin):
    """Handler for the endpoint to post claims."""
    def __init__(self, partitions_controller, catalogue_controller,
                 cache, selector):
        super(ClaimCreate, self).__init__(
            partitions_controller, catalogue_controller, cache,
            selector, methods=['post'])


class Claim(forward.ForwardMixin):
    """Handler for dealing with claims directly."""
    def __init__(self, partitions_controller, catalogue_controller,
                 cache, selector):
        super(Claim, self).__init__(
            partitions_controller, catalogue_controller, cache,
            selector, methods=['patch', 'delete', 'get'])


class MessageBulk(forward.ForwardMixin):
    """Handler for bulk message operations."""
    def __init__(self, partitions_controller, catalogue_controller,
                 cache, selector):
        super(MessageBulk, self).__init__(
            partitions_controller, catalogue_controller, cache,
            selector, methods=['get', 'delete', 'post'])


class Message(forward.ForwardMixin):
    """Handler for individual messages."""
    def __init__(self, partitions_controller, catalogue_controller,
                 cache, selector):
        super(Message, self).__init__(
            partitions_controller, catalogue_controller, cache,
            selector, methods=['get', 'delete'])


class Stats(forward.ForwardMixin):
    """Handler for forwarding queue stats requests."""
    def __init__(self, partitions_controller, catalogue_controller,
                 cache, selector):
        super(Stats, self).__init__(
            partitions_controller, catalogue_controller, cache,
            selector, methods=['get'])

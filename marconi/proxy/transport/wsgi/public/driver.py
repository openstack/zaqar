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
"""marconi-proxy (public): maps project/queue to partitions.

Forwards requests to the appropriate marconi queues server.
"""

from marconi.proxy.transport.wsgi import (
    driver, forward, health, metadata,
    queues, v1
)


class Driver(driver.DriverBase):

    def __init(self, storage, cache):
        super(Driver, self).__init__(storage, cache)

    @property
    def bridge(self):
        forwarder_args = (self.partitions, self.catalogue,
                          self.cache, self.selector)
        return [
            ('/health', health.Resource()),

            # NOTE(cpp-cabrera): queue handling routes
            ('/queues',
             queues.Listing(self.catalogue)),
            ('/queues/{queue}',
             queues.Resource(*forwarder_args)),

            # NOTE(cpp-cabrera): Marconi forwarded routes
            ('/queues/{queue}/claims',
             forward.ClaimCreate(*forwarder_args)),
            ('/queues/{queue}/claims/{cid}',
             forward.Claim(*forwarder_args)),
            ('/queues/{queue}/messages',
             forward.MessageBulk(*forwarder_args)),
            ('/queues/{queue}/messages/{mid}',
             forward.Message(*forwarder_args)),
            ('/queues/{queue}/metadata',
             metadata.Resource(*forwarder_args)),
            ('/queues/{queue}/stats',
             forward.Stats(*forwarder_args)),
            ('', v1.Resource(self.partitions))
        ]

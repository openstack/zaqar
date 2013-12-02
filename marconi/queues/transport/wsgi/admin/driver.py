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
"""marconi-queues (admin): interface for managing partitions."""

from marconi.common.transport.wsgi import health
from marconi.queues.transport.wsgi.public import driver as public_driver
from marconi.queues.transport.wsgi import shards


class Driver(public_driver.Driver):

    @property
    def bridge(self):
        shards_controller = self._control.shards_controller
        return super(Driver, self).bridge + [
            ('/shards',
             shards.Listing(shards_controller)),
            ('/shards/{shard}',
             shards.Resource(shards_controller)),
            ('/health',
             health.Resource(self._storage))
        ]

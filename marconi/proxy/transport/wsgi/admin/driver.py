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
"""marconi-proxy (admin): interface for managing partitions."""

from marconi.proxy.transport.wsgi import (
    catalogue, driver, health, partitions,
)


class Driver(driver.DriverBase):
    def __init__(self, storage, cache):
        super(Driver, self).__init__(storage, cache)

    @property
    def bridge(self):
        return [
            ('/partitions',
             partitions.Listing(self.partitions)),
            ('/partitions/{partition}',
             partitions.Resource(self.partitions)),
            ('/catalogue',
             catalogue.Listing(self.catalogue)),
            ('/catalogue/{queue}',
             catalogue.Resource(self.catalogue)),
            ('/health',
             health.Resource())
        ]

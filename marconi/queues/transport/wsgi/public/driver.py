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
"""marconi-queues (public): handles all the routes for queuing,
messaging, and claiming.
"""


from marconi.common.transport.wsgi import health
from marconi.queues.transport.wsgi import (
    claims, driver, messages, metadata, queues, stats, v1,
)


class Driver(driver.DriverBase):

    @property
    def bridge(self):
        queue_controller = self._storage.queue_controller
        message_controller = self._storage.message_controller
        claim_controller = self._storage.claim_controller
        return [
            # Home
            ('/',
             v1.V1Resource()),

            # Queues Endpoints
            ('/queues',
             queues.CollectionResource(self._validate,
                                       queue_controller)),
            ('/queues/{queue_name}',
             queues.ItemResource(queue_controller,
                                 message_controller)),
            ('/queues/{queue_name}/stats',
             stats.Resource(queue_controller)),
            ('/queues/{queue_name}/metadata',
             metadata.Resource(self._wsgi_conf, self._validate,
                               queue_controller)),

            # Messages Endpoints
            ('/queues/{queue_name}/messages',
             messages.CollectionResource(self._wsgi_conf,
                                         self._validate,
                                         message_controller)),
            ('/queues/{queue_name}/messages/{message_id}',
             messages.ItemResource(message_controller)),

            # Claims Endpoints
            ('/queues/{queue_name}/claims',
             claims.CollectionResource(self._wsgi_conf,
                                       self._validate,
                                       claim_controller)),
            ('/queues/{queue_name}/claims/{claim_id}',
             claims.ItemResource(self._wsgi_conf,
                                 self._validate,
                                 claim_controller)),

            # Health
            ('/health',
             health.Resource(self._storage))
        ]

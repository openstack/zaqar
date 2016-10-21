# Copyright (c) 2013 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

from zaqar.common import decorators
from zaqar.transport.wsgi.v2_0 import claims
from zaqar.transport.wsgi.v2_0 import flavors
from zaqar.transport.wsgi.v2_0 import health
from zaqar.transport.wsgi.v2_0 import homedoc
from zaqar.transport.wsgi.v2_0 import messages
from zaqar.transport.wsgi.v2_0 import ping
from zaqar.transport.wsgi.v2_0 import pools
from zaqar.transport.wsgi.v2_0 import purge
from zaqar.transport.wsgi.v2_0 import queues
from zaqar.transport.wsgi.v2_0 import stats
from zaqar.transport.wsgi.v2_0 import subscriptions
from zaqar.transport.wsgi.v2_0 import urls


VERSION = {
    'id': '2',
    'status': 'CURRENT',
    'updated': '2014-9-24T04:06:47Z',
    'media-types': [
        {
            'base': 'application/json',
            'type': 'application/vnd.openstack.messaging-v2+json'
        }
    ],
    'links': [
        {
            'href': '/v2/',
            'rel': 'self'
        }
    ]
}


@decorators.api_version_manager(VERSION)
def public_endpoints(driver, conf):
    queue_controller = driver._storage.queue_controller
    message_controller = driver._storage.message_controller
    claim_controller = driver._storage.claim_controller
    subscription_controller = driver._storage.subscription_controller

    defaults = driver._defaults

    return [
        # Home
        ('/',
         homedoc.Resource(conf)),

        # Queues Endpoints
        ('/queues',
         queues.CollectionResource(driver._validate,
                                   queue_controller)),
        ('/queues/{queue_name}',
         queues.ItemResource(driver._validate,
                             queue_controller,
                             message_controller)),
        ('/queues/{queue_name}/stats',
         stats.Resource(queue_controller)),
        ('/queues/{queue_name}/purge',
         purge.Resource(driver)),
        # Messages Endpoints
        ('/queues/{queue_name}/messages',
         messages.CollectionResource(driver._wsgi_conf,
                                     driver._validate,
                                     message_controller,
                                     queue_controller,
                                     defaults.message_ttl)),
        ('/queues/{queue_name}/messages/{message_id}',
         messages.ItemResource(message_controller)),

        # Claims Endpoints
        ('/queues/{queue_name}/claims',
         claims.CollectionResource(driver._wsgi_conf,
                                   driver._validate,
                                   claim_controller,
                                   defaults.claim_ttl,
                                   defaults.claim_grace)),
        ('/queues/{queue_name}/claims/{claim_id}',
         claims.ItemResource(driver._wsgi_conf,
                             driver._validate,
                             claim_controller,
                             defaults.claim_ttl,
                             defaults.claim_grace)),

        # Ping
        ('/ping',
         ping.Resource(driver._storage)),

        # Subscription Endpoints
        ('/queues/{queue_name}/subscriptions',
         subscriptions.CollectionResource(driver._validate,
                                          subscription_controller,
                                          defaults.subscription_ttl,
                                          queue_controller,
                                          conf)),

        ('/queues/{queue_name}/subscriptions/{subscription_id}',
         subscriptions.ItemResource(driver._validate,
                                    subscription_controller)),

        ('/queues/{queue_name}/subscriptions/{subscription_id}/confirm',
         subscriptions.ConfirmResource(driver._validate,
                                       subscription_controller,
                                       conf)),

        # Pre-Signed URL Endpoint
        ('/queues/{queue_name}/share', urls.Resource(driver)),
    ]


@decorators.api_version_manager(VERSION)
def private_endpoints(driver, conf):

    catalogue = [
        # Health
        ('/health',
         health.Resource(driver._storage)),
    ]

    if conf.pooling:
        pools_controller = driver._control.pools_controller
        flavors_controller = driver._control.flavors_controller
        validate = driver._validate

        catalogue.extend([
            ('/pools',
             pools.Listing(pools_controller, validate)),
            ('/pools/{pool}',
             pools.Resource(pools_controller)),
            ('/flavors',
             flavors.Listing(flavors_controller, pools_controller,
                             validate)),
            ('/flavors/{flavor}',
             flavors.Resource(flavors_controller, pools_controller)),
        ])

    return catalogue

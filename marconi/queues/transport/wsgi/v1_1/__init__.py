from marconi.queues.transport.wsgi.v1_1 import claims
from marconi.queues.transport.wsgi.v1_1 import health
from marconi.queues.transport.wsgi.v1_1 import homedoc
from marconi.queues.transport.wsgi.v1_1 import messages
from marconi.queues.transport.wsgi.v1_1 import metadata
from marconi.queues.transport.wsgi.v1_1 import ping
from marconi.queues.transport.wsgi.v1_1 import queues
from marconi.queues.transport.wsgi.v1_1 import shards
from marconi.queues.transport.wsgi.v1_1 import stats


def public_endpoints(driver):
    queue_controller = driver._storage.queue_controller
    message_controller = driver._storage.message_controller
    claim_controller = driver._storage.claim_controller

    return [
        # Home
        ('/',
         homedoc.Resource()),

        # Queues Endpoints
        ('/queues',
         queues.CollectionResource(driver._validate,
                                   queue_controller)),
        ('/queues/{queue_name}',
         queues.ItemResource(queue_controller,
                             message_controller)),
        ('/queues/{queue_name}/stats',
         stats.Resource(queue_controller)),
        ('/queues/{queue_name}/metadata',
         metadata.Resource(driver._wsgi_conf, driver._validate,
                           queue_controller)),

        # Messages Endpoints
        ('/queues/{queue_name}/messages',
         messages.CollectionResource(driver._wsgi_conf,
                                     driver._validate,
                                     message_controller)),
        ('/queues/{queue_name}/messages/{message_id}',
         messages.ItemResource(message_controller)),

        # Claims Endpoints
        ('/queues/{queue_name}/claims',
         claims.CollectionResource(driver._wsgi_conf,
                                   driver._validate,
                                   claim_controller)),
        ('/queues/{queue_name}/claims/{claim_id}',
         claims.ItemResource(driver._wsgi_conf,
                             driver._validate,
                             claim_controller)),

        # Health
        ('/health',
         health.Resource(driver._storage)),

        # Ping
        ('/ping',
         ping.Resource(driver._storage))
    ]


def private_endpoints(driver):
    shards_controller = driver._control.shards_controller

    return [
        ('/shards',
         shards.Listing(shards_controller)),
        ('/shards/{shard}',
         shards.Resource(shards_controller)),
    ]

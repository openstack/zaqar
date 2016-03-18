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

import json


# NOTE(kgriffs): http://tools.ietf.org/html/draft-nottingham-json-home-03
JSON_HOME = {
    'resources': {
        # -----------------------------------------------------------------
        # Queues
        # -----------------------------------------------------------------
        'rel/queues': {
            'href-template': '/v1.1/queues{?marker,limit,detailed}',
            'href-vars': {
                'marker': 'param/marker',
                'limit': 'param/queue_limit',
                'detailed': 'param/detailed',
            },
            'hints': {
                'allow': ['GET'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        'rel/queue': {
            'href-template': '/v1.1/queues/{queue_name}',
            'href-vars': {
                'queue_name': 'param/queue_name',
            },
            'hints': {
                'allow': ['PUT', 'DELETE'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        'rel/queue_stats': {
            'href-template': '/v1.1/queues/{queue_name}/stats',
            'href-vars': {
                'queue_name': 'param/queue_name',
            },
            'hints': {
                'allow': ['GET'],
                'formats': {
                    'application/json': {},
                },
            },
        },

        # -----------------------------------------------------------------
        # Messages
        # -----------------------------------------------------------------
        'rel/messages': {
            'href-template': ('/v1.1/queues/{queue_name}/messages'
                              '{?marker,limit,echo,include_claimed}'),
            'href-vars': {
                'queue_name': 'param/queue_name',
                'marker': 'param/marker',
                'limit': 'param/messages_limit',
                'echo': 'param/echo',
                'include_claimed': 'param/include_claimed',
            },
            'hints': {
                'allow': ['GET'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        'rel/post_messages': {
            'href-template': '/v1.1/queues/{queue_name}/messages',
            'href-vars': {
                'queue_name': 'param/queue_name',
            },
            'hints': {
                'allow': ['POST'],
                'formats': {
                    'application/json': {},
                },
                'accept-post': ['application/json'],
            },
        },
        'rel/messages_delete': {
            'href-template': '/v1.1/queues/{queue_name}/messages{?ids,pop}',
            'href-vars': {
                'queue_name': 'param/queue_name',
                'ids': 'param/ids',
                'pop': 'param/pop'
            },
            'hints': {
                'allow': [
                    'DELETE'
                ],
                'formats': {
                    'application/json': {}
                }
            }
        },
        'rel/message_delete': {
            'href-template': '/v1.1/queues/{queue_name}/messages/{message_id}{?claim}',  # noqa
            'href-vars': {
                'queue_name': 'param/queue_name',
                'message_id': 'param/message_id',
                'claim': 'param/claim_id'
            },
            'hints': {
                'allow': [
                    'DELETE'
                ],
                'formats': {
                    'application/json': {}
                }
            }
        },

        # -----------------------------------------------------------------
        # Claims
        # -----------------------------------------------------------------
        'rel/claim': {
            'href-template': '/v1.1/queues/{queue_name}/claims/{claim_id}',
            'href-vars': {
                'queue_name': 'param/queue_name',
                'claim_id': 'param/claim_id',
            },
            'hints': {
                'allow': ['GET'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        'rel/post_claim': {
            'href-template': '/v1.1/queues/{queue_name}/claims{?limit}',
            'href-vars': {
                'queue_name': 'param/queue_name',
                'limit': 'param/claim_limit',
            },
            'hints': {
                'allow': ['POST'],
                'formats': {
                    'application/json': {},
                },
                'accept-post': ['application/json']
            },
        },
        'rel/patch_claim': {
            'href-template': '/v1.1/queues/{queue_name}/claims/{claim_id}',
            'href-vars': {
                'queue_name': 'param/queue_name',
                'claim_id': 'param/claim_id',
            },
            'hints': {
                'allow': ['PATCH'],
                'formats': {
                    'application/json': {},
                },
                'accept-post': ['application/json']
            },
        },
        'rel/delete_claim': {
            'href-template': '/v1.1/queues/{queue_name}/claims/{claim_id}',
            'href-vars': {
                'queue_name': 'param/queue_name',
                'claim_id': 'param/claim_id',
            },
            'hints': {
                'allow': ['DELETE'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        # -----------------------------------------------------------------
        # Ping
        # -----------------------------------------------------------------
        'rel/ping': {
            'href-template': '/v1.1/ping',
            'hints': {
                'allow': ['GET'],
                'formats': {
                    'application/json': {},
                }
            }
        }
    }
}


ADMIN_RESOURCES = {
    # -----------------------------------------------------------------
    # Pools
    # -----------------------------------------------------------------
    'rel/pools': {
        'href-template': '/v1.1/pools{?detailed,limit,marker}',
        'href-vars': {
            'detailed': 'param/detailed',
            'limit': 'param/pool_limit',
            'marker': 'param/marker',
        },
        'hints': {
            'allow': ['GET'],
            'formats': {
                'application/json': {},
            },
        },
    },
    'rel/pool': {
        'href-template': '/v1.1/pools/{pool_name}',
        'href-vars': {
            'pool_name': 'param/pool_name',
        },
        'hints': {
            'allow': ['GET', 'PUT', 'PATCH', 'DELETE'],
            'formats': {
                'application/json': {},
            },
        },
    },

    # -----------------------------------------------------------------
    # Flavors
    # -----------------------------------------------------------------
    'rel/flavors': {
        'href-template': '/v1.1/flavors{?detailed,limit,marker}',
        'href-vars': {
            'detailed': 'param/detailed',
            'limit': 'param/flavor_limit',
            'marker': 'param/marker',
        },
        'hints': {
            'allow': ['GET'],
            'formats': {
                'application/json': {},
            },
        },
    },
    'rel/flavor': {
        'href-template': '/v1.1/flavors/{flavor_name}',
        'href-vars': {
            'flavor_name': 'param/flavor_name',
        },
        'hints': {
            'allow': ['GET', 'PUT', 'PATCH', 'DELETE'],
            'formats': {
                'application/json': {},
            },
        },
    },

    # -----------------------------------------------------------------
    # Health
    # -----------------------------------------------------------------
    'rel/health': {
        'href': '/v1.1/health',
        'hints': {
            'allow': ['GET'],
            'formats': {
                'application/json': {},
            },
        },
    },
}


class Resource(object):

    def __init__(self, conf):
        if conf.admin_mode:
            JSON_HOME['resources'].update(ADMIN_RESOURCES)

        document = json.dumps(JSON_HOME, ensure_ascii=False, indent=4)
        self.document_utf8 = document.encode('utf-8')

    def on_get(self, req, resp, project_id):
        resp.data = self.document_utf8

        resp.content_type = 'application/json-home'
        resp.cache_control = ['max-age=86400']
        # status defaults to 200

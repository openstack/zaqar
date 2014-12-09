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
            'href-template': '/v1/queues{?marker,limit,detailed}',
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
            'href-template': '/v1/queues/{queue_name}',
            'href-vars': {
                'queue_name': 'param/queue_name',
            },
            'hints': {
                'allow': ['GET', 'HEAD', 'PUT', 'DELETE'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        'rel/queue-metadata': {
            'href-template': '/v1/queues/{queue_name}/metadata',
            'href-vars': {
                'queue_name': 'param/queue_name',
            },
            'hints': {
                'allow': ['GET', 'PUT'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        'rel/queue-stats': {
            'href-template': '/v1/queues/{queue_name}/stats',
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
            'href-template': ('/v1/queues/{queue_name}/messages'
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
        'rel/post-messages': {
            'href-template': '/v1/queues/{queue_name}/messages',
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

        # -----------------------------------------------------------------
        # Claims
        # -----------------------------------------------------------------
        'rel/claim': {
            'href-template': '/v1/queues/{queue_name}/claims{?limit}',
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

    }
}


class Resource(object):

    def __init__(self):
        document = json.dumps(JSON_HOME, ensure_ascii=False, indent=4)
        self.document_utf8 = document.encode('utf-8')

    def on_get(self, req, resp, project_id):
        resp.data = self.document_utf8

        resp.content_type = 'application/json-home'
        resp.cache_control = ['max-age=86400']
        # status defaults to 200

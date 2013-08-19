# Copyright (c) 2013 Rackspace, Inc.
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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import json

DOC_ROOT = 'http://docs.openstack-marconi.org'
"""Root URL for documents refered to in the home document."""


# NOTE(kgriffs): http://tools.ietf.org/html/draft-nottingham-json-home-03
JSON_HOME = {
    'resources': {
        #------------------------------------------------------------------
        # Diagnostics
        #------------------------------------------------------------------
        DOC_ROOT + '/rel/health': {
            'href': '/health',
            'hints': {
                'allow': ['GET', 'HEAD'],
            },
        },

        #------------------------------------------------------------------
        # Queues
        #------------------------------------------------------------------
        DOC_ROOT + '/rel/queues': {
            'href-template': '/queues{?marker,limit,detailed}',
            'href-vars': {
                'marker': DOC_ROOT + '/param/marker',
                'limit': DOC_ROOT + '/param/queue_limit',
                'detailed': DOC_ROOT + '/param/detailed',
            },
            'hints': {
                'allow': ['GET'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        DOC_ROOT + '/rel/queue': {
            'href-template': '/queues/{queue_name}',
            'href-vars': {
                'queue_name': DOC_ROOT + '/param/queue_name',
            },
            'hints': {
                'allow': ['PUT', 'DELETE'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        DOC_ROOT + '/rel/queue-metadata': {
            'href-template': '/queues/{queue_name}/metadata',
            'href-vars': {
                'queue_name': DOC_ROOT + '/param/queue_name',
            },
            'hints': {
                'allow': ['GET', 'PUT'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        DOC_ROOT + '/rel/queue-stats': {
            'href-template': '/queues/{queue_name}/stats',
            'href-vars': {
                'queue_name': DOC_ROOT + '/param/queue_name',
            },
            'hints': {
                'allow': ['GET'],
                'formats': {
                    'application/json': {},
                },
            },
        },

        #------------------------------------------------------------------
        # Messages
        #------------------------------------------------------------------
        DOC_ROOT + '/rel/messages': {
            'href-template': ('/queues/{queue_name}/messages'
                              '{?marker,limit,echo,include_claimed}'),
            'href-vars': {
                'queue_name': DOC_ROOT + '/param/queue_name',
                'marker': DOC_ROOT + '/param/marker',
                'limit': DOC_ROOT + '/param/messages_limit',
                'echo': DOC_ROOT + '/param/echo',
                'include_claimed': DOC_ROOT + '/param/include_claimed',
            },
            'hints': {
                'allow': ['GET'],
                'formats': {
                    'application/json': {},
                },
            },
        },
        DOC_ROOT + '/rel/post-messages': {
            'href-template': '/v1/queues/{queue_name}/messages',
            'href-vars': {
                'queue_name': DOC_ROOT + '/param/queue_name',
            },
            'hints': {
                'allow': ['POST'],
                'formats': {
                    'application/json': {},
                },
                'accept-post': ['application/json'],
            },
        },

        #------------------------------------------------------------------
        # Claims
        #------------------------------------------------------------------
        DOC_ROOT + '/rel/claim': {
            'href-template': '/v1/queues/{queue_name}/claims{?limit}',
            'href-vars': {
                'queue_name': DOC_ROOT + '/param/queue_name',
                'limit': DOC_ROOT + '/param/claim_limit',
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


class V1Resource(object):

    def __init__(self):
        document = json.dumps(JSON_HOME, ensure_ascii=False, indent=4)
        self.document_utf8 = document.encode('utf-8')

    def on_get(self, req, resp, project_id):
        resp.data = self.document_utf8

        resp.content_type = 'application/json-home'
        resp.cache_control = ['max-age=86400']
        # status defaults to 200

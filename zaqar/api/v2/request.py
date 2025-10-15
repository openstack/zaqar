# Copyright (c) 2013 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from zaqar.common.api import api
from zaqar.common import consts


class RequestSchema(api.Api):

    headers = {
        'User-Agent': {'type': 'string'},
        'Date': {'type': 'string'},
        'Accept': {'type': 'string'},
        'Client-ID': {'type': 'string'},
        'X-Project-ID': {'type': 'string'},
        'X-Auth-Token': {'type': 'string'}
    }

    schema = {

        # Base
        'get_home_doc': {
            'properties': {
                'action': {'enum': ['get_home_doc']},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                }
            },
            'required': ['action', 'headers'],
            'admin': True,
        },

        'check_node_health': {
            'properties': {
                'action': {'enum': ['check_node_health']},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                }
            },
            'required': ['action', 'headers'],
            'admin': True,
        },

        'ping_node': {
            'properties': {
                'action': {'enum': ['ping_node']},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                }
            },
            'required': ['action', 'headers'],
            'admin': True,
        },
        'authenticate': {
            'properties': {
                'action': {'enum': ['authenticate']},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['X-Project-ID', 'X-Auth-Token']
                }
            },
            'required': ['action', 'headers'],
        },

        # Queues
        consts.QUEUE_LIST: {
            'properties': {
                'action': {'enum': [consts.QUEUE_LIST]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'marker': {'type': 'string'},
                        'limit': {'type': 'integer'},
                        'detailed': {'type': 'boolean'}
                    }
                }
            },
            'required': ['action', 'headers']
        },

        consts.QUEUE_CREATE: {
            'properties': {
                'action': {'enum': [consts.QUEUE_CREATE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']},
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                    },
                    'required': ['queue_name'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.QUEUE_DELETE: {
            'properties': {
                'action': {'enum': [consts.QUEUE_DELETE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                    },
                    'required': ['queue_name']
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.QUEUE_GET: {
            'properties': {
                'action': {'enum': [consts.QUEUE_GET]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                    },
                    'required': ['queue_name'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.QUEUE_GET_STATS: {
            'properties': {
                'action': {'enum': [consts.QUEUE_GET_STATS]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                    },
                    'required': ['queue_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True
        },

        consts.QUEUE_PURGE: {
            'properties': {
                'action': {'enum': [consts.QUEUE_PURGE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']},
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'resource_types': {'type': 'array'},
                    },
                    'required': ['queue_name'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        # Messages
        consts.MESSAGE_LIST: {
            'properties': {
                'action': {'enum': [consts.MESSAGE_LIST]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'marker': {'type': 'string'},
                        'limit': {'type': 'integer'},
                        'echo': {'type': 'boolean'},
                        'include_claimed': {'type': 'boolean'},
                    },
                    'required': ['queue_name'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.MESSAGE_GET: {
            'properties': {
                'action': {'enum': [consts.MESSAGE_GET]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'message_id': {'type': 'string'},
                    },
                    'required': ['queue_name', 'message_id'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.MESSAGE_GET_MANY: {
            'properties': {
                'action': {'enum': [consts.MESSAGE_GET_MANY]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'message_ids': {'type': 'array'},
                    },
                    'required': ['queue_name', 'message_ids'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.MESSAGE_POST: {
            'properties': {
                'action': {'enum': [consts.MESSAGE_POST]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'messages': {'type': 'array'},
                    },
                    'required': ['queue_name', 'messages'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.MESSAGE_DELETE: {
            'properties': {
                'action': {'enum': [consts.MESSAGE_DELETE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'message_id': {'type': 'string'},
                        'claim_id': {'type': 'string'}
                    },
                    'required': ['queue_name', 'message_id'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.MESSAGE_DELETE_MANY: {
            'properties': {
                'action': {'enum': [consts.MESSAGE_DELETE_MANY]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'message_ids': {'type': 'array'},
                        'claim_ids': {'type': 'array'},
                        'pop': {'type': 'integer'}
                    },
                    'required': ['queue_name'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        # Claims
        consts.CLAIM_CREATE: {
            'properties': {
                'action': {'enum': [consts.CLAIM_CREATE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'limit': {'type': 'integer'},
                        'ttl': {'type': 'integer'},
                        'grace': {'type': 'integer'}
                    },
                    'required': ['queue_name'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.CLAIM_GET: {
            'properties': {
                'action': {'enum': [consts.CLAIM_GET]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'claim_id': {'type': 'string'}
                    },
                    'required': ['queue_name', 'claim_id'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.CLAIM_UPDATE: {
            'properties': {
                'action': {'enum': [consts.CLAIM_UPDATE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'claim_id': {'type': 'string'},
                        'ttl': {'type': 'integer'}
                    },
                    'required': ['queue_name', 'claim_id'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.CLAIM_DELETE: {
            'properties': {
                'action': {'enum': [consts.CLAIM_DELETE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'claim_id': {'type': 'string'}
                    },
                    'required': ['queue_name', 'claim_id'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        # Pools
        consts.POOL_LIST: {
            'properties': {
                'action': {'enum': [consts.POOL_LIST]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'pool_name': {'type': 'string'},
                        'limit': {'type': 'integer'},
                        'marker': {'type': 'string'}
                    },
                    'required': ['pool_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True,
        },

        consts.POOL_CREATE: {
            'properties': {
                'action': {'enum': [consts.POOL_CREATE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'pool_name': {'type': 'string'},
                        'weight': {'type': 'integer'},
                        'uri': {'type': 'string'},
                        'options': {'type': 'object'},
                    },
                    'required': ['pool_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True,
        },

        consts.POOL_UPDATE: {
            'properties': {
                'action': {'enum': [consts.POOL_UPDATE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'pool_name': {'type': 'string'},
                        'weight': {'type': 'integer'},
                        'uri': {'type': 'string'},
                        'options': {'type': 'object'},
                    },
                    'required': ['pool_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True,
        },

        consts.POOL_GET: {
            'properties': {
                'action': {'enum': [consts.POOL_GET]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'pool_name': {'type': 'string'},
                        'detailed': {'type': 'boolean'}
                    },
                    'required': ['pool_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True,
        },

        consts.POOL_DELETE: {
            'properties': {
                'action': {'enum': [consts.POOL_DELETE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'pool_name': {'type': 'string'}
                    },
                    'required': ['pool_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True,
        },

        # Flavors
        consts.FLAVOR_LIST: {
            'properties': {
                'action': {'enum': [consts.FLAVOR_LIST]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'flavor_name': {'type': 'string'},
                        'limit': {'type': 'integer'},
                        'marker': {'type': 'string'}
                    },
                    'required': ['flavor_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True,
        },

        consts.FLAVOR_CREATE: {
            'properties': {
                'action': {'enum': [consts.FLAVOR_CREATE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'flavor_name': {'type': 'string'},
                        'pool_name': {'type': 'string'},
                        'capabilities': {'type': 'object'},
                    },
                    'required': ['flavor_name', 'pool_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True,
        },

        consts.FLAVOR_UPDATE: {
            'properties': {
                'action': {'enum': [consts.FLAVOR_UPDATE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'flavor_name': {'type': 'string'},
                        'pool_name': {'type': 'string'},
                        'capabilities': {'type': 'object'},
                    },
                    'required': ['flavor_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True,
        },

        consts.FLAVOR_GET: {
            'properties': {
                'action': {'enum': [consts.FLAVOR_GET]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'flavor_name': {'type': 'string'},
                        'detailed': {'type': 'boolean'}
                    },
                    'required': ['flavor_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True,
        },

        consts.FLAVOR_DELETE: {
            'properties': {
                'action': {'enum': [consts.FLAVOR_DELETE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'flavor_name': {'type': 'string'}
                    },
                    'required': ['flavor_name'],
                }
            },
            'required': ['action', 'headers', 'body'],
            'admin': True,
        },

        # Subscriptions
        consts.SUBSCRIPTION_LIST: {
            'properties': {
                'action': {'enum': [consts.SUBSCRIPTION_LIST]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                    },
                    'required': ['queue_name'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.SUBSCRIPTION_CREATE: {
            'properties': {
                'action': {'enum': [consts.SUBSCRIPTION_CREATE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']},
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'subscriber': {'type': 'string'},
                        'ttl': {'type': 'integer'},
                        'options': {'type': 'object'},
                    },
                    'required': ['queue_name', ],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.SUBSCRIPTION_DELETE: {
            'properties': {
                'action': {'enum': [consts.SUBSCRIPTION_DELETE]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'subscription_id': {'type': 'string'},
                    },
                    'required': ['queue_name', 'subscription_id']
                }
            },
            'required': ['action', 'headers', 'body']
        },

        consts.SUBSCRIPTION_GET: {
            'properties': {
                'action': {'enum': [consts.SUBSCRIPTION_GET]},
                'headers': {
                    'type': 'object',
                    'properties': headers,
                    'required': ['Client-ID', 'X-Project-ID']
                },
                'body': {
                    'type': 'object',
                    'properties': {
                        'queue_name': {'type': 'string'},
                        'subscription_id': {'type': 'string'},
                    },
                    'required': ['queue_name', 'subscription_id'],
                }
            },
            'required': ['action', 'headers', 'body']
        },
    }

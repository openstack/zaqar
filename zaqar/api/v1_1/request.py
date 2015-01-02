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

        # Queues
        'queue_list': {
            'properties': {
                'action': {'enum': ['queue_list']},
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

        'queue_create': {
            'properties': {
                'action': {'enum': ['queue_create']},
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

        'queue_delete': {
            'properties': {
                'action': {'enum': ['queue_delete']},
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

        'queue_get': {
            'properties': {
                'action': {'enum': ['queue_get']},
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

        'queue_get_stats': {
            'properties': {
                'action': {'enum': ['queue_get_stats']},
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

        # Messages
        'message_list': {
            'properties': {
                'action': {'enum': ['message_list']},
                'headers':  {
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

        'message_get': {
            'properties': {
                'action': {'enum': ['message_get']},
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

        'message_get_many': {
            'properties': {
                'action': {'enum': ['message_get_many']},
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

        'message_post': {
            'properties': {
                'action': {'enum': ['message_post']},
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

        'message_delete': {
            'properties': {
                'action': {'enum': ['message_delete']},
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

        'message_delete_many': {
            'properties': {
                'action': {'enum': ['message_delete_many']},
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
                        'pop': {'type': 'integer'}
                    },
                    'required': ['queue_name', 'message_ids'],
                }
            },
            'required': ['action', 'headers', 'body']
        },

        # Claims
        'claim_create': {
            'properties': {
                'action': {'enum': ['claim_create']},
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

        'claim_get': {
            'properties': {
                'action': {'enum': ['claim_get']},
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

        'claim_update': {
            'properties': {
                'action': {'enum': ['claim_update']},
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

        'claim_delete': {
            'properties': {
                'action': {'enum': ['claim_delete']},
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
        'pool_list': {
            'properties': {
                'action': {'enum': ['pool_list']},
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

        'pool_create': {
            'properties': {
                'action': {'enum': ['pool_create']},
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

        'pool_update': {
            'properties': {
                'action': {'enum': ['pool_update']},
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

        'pool_get': {
            'properties': {
                'action': {'enum': ['pool_get']},
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

        'pool_delete': {
            'properties': {
                'action': {'enum': ['pool_delete']},
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
        'flavor_list': {
            'properties': {
                'action': {'enum': ['flavor_list']},
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

        'flavor_create': {
            'properties': {
                'action': {'enum': ['flavor_create']},
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

        'flavor_update': {
            'properties': {
                'action': {'enum': ['flavor_update']},
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

        'flavor_get': {
            'properties': {
                'action': {'enum': ['flavor_get']},
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

        'flavor_delete': {
            'properties': {
                'action': {'enum': ['flavor_delete']},
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
    }
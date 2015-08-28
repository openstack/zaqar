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

from zaqar.api.v1 import request as v1


class RequestSchema(v1.RequestSchema):

    headers = v1.RequestSchema.headers
    schema = v1.RequestSchema.schema

    schema.update({

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
    })

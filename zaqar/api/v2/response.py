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
# See the License for the specific language governing permissions and
# limitations under the License.

from zaqar.common.api import api


class ResponseSchema(api.Api):

    """Define validation schema for json response."""

    def __init__(self, limits):
        self.limits = limits

        age = {
            "type": "number",
            "minimum": 0
        }

        message = {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                },
                "href": {
                    "type": "string",
                    "pattern": "^(/v1/queues/[a-zA-Z0-9_-]{1,64}"
                    "/messages/[a-zA-Z0-9_-]+)(\?claim_id=[a-zA-Z0-9_-]+)?$"
                },
                "age": age,
                "ttl": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": self.limits.max_message_ttl
                },

                "body": {
                    "type": "object"
                }
            },
            "required": ["href", "ttl", "age", "body", "id"],
            "additionalProperties": False,
        }

        claim_href = {
            "type": "string",
            "pattern": "^(/v2/queues/[a-zA-Z0-9_-]{1,64}"
            "/messages/[a-zA-Z0-9_-]+)"
            "\?claim_id=[a-zA-Z0-9_-]+$"
        }

        flavor = {
            'type': 'object',
            'properties': {
                'href': {
                    'type': 'string',
                    'pattern': '^/v2/flavors/[a-zA-Z0-9_-]{1,64}$'
                },
                'pool': {
                    'type': 'string',
                },
                'project': {
                    'type': 'string'
                },
                'capabilities': {
                    'type': 'object',
                    'additionalProperties': True
                }
            },
            'required': ['href', 'pool', 'project'],
            'additionalProperties': False,
        }

        self.schema = {
            'message_get_many': {
                'type': 'object',
                'properties': {
                    'messages': {
                        "type": "array",
                        "items": message,
                        "minItems": 1,
                        "maxItems": self.limits.max_messages_per_page
                    }
                },
                'required': ['messages'],
                'additionalProperties': False,
            },

            'queue_list': {
                'type': 'object',
                'properties': {
                    'links': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'rel': {
                                    'type': 'string',
                                    'enum': ['next'],
                                },
                                'href': {
                                    'type': 'string',
                                    "pattern": "^/v2/queues\?",
                                }
                            },
                            'required': ['rel', 'href'],
                            'additionalProperties': False,
                        },
                        'minItems': 1,
                        'maxItems': 1,
                    },

                    'queues': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'name': {
                                    'type': 'string',
                                    'pattern': '^[a-zA-Z0-9_-]{1,64}$'
                                },
                                'href': {
                                    'type': 'string',
                                    'pattern': '^/v2/queues/'
                                               '[a-zA-Z0-9_-]{1,64}$',
                                },
                                'metadata': {
                                    'type': 'object',
                                }
                            },
                            'required': ['name', 'href'],
                            'additionalProperties': False,
                        },
                        'minItems': 1,
                        'maxItems': self.limits.max_queues_per_page,
                    }
                },
                'required': ['links', 'queues'],
                'additionalProperties': False,
            },

            'queue_stats': {
                'type': 'object',
                'properties': {
                    'messages': {
                        'type': 'object',
                        'properties': {
                            'free': {
                                'type': 'number',
                                'minimum': 0
                            },
                            'claimed': {
                                'type': 'number',
                                'minimum': 0
                            },
                            'total': {
                                'type': 'number',
                                'minimum': 0
                            },
                            'oldest': {
                                'type': 'object'
                            },
                            'newest': {
                                'type': 'object'
                            }

                        },
                        'required': ['free', 'claimed', 'total'],
                        'additionalProperties': False
                    }
                },
                'required': ['messages'],
                'additionalProperties': False
            },

            'pool_list': {
                'type': 'object',
                'properties': {
                    'links': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'rel': {
                                    'type': 'string'
                                },
                                'href': {
                                    'type': 'string',
                                    'pattern': '^/v2/pools\?'
                                }
                            },
                            'required': ['rel', 'href'],
                            'additionalProperties': False
                        }
                    },
                    'pools': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'href': {
                                    'type': 'string',
                                    'pattern': '^/v2/'
                                               'pools/[a-zA-Z0-9_-]{1,64}$'
                                },
                                'weight': {
                                    'type': 'number',
                                    'minimum': -1
                                },
                                'name': {
                                    'type': 'string'
                                },
                                'uri': {
                                    'type': 'string'
                                },
                                'group': {
                                    'type': ['string', 'null']
                                },
                                'options': {
                                    'type': 'object',
                                    'additionalProperties': True
                                }
                            },
                            'required': ['href', 'weight', 'uri', 'group'],
                            'additionalProperties': False,
                        },
                    }
                },
                'required': ['links', 'pools'],
                'additionalProperties': False
            },

            'message_list': {
                'type': 'object',
                'properties': {
                    'links': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'rel': {
                                    'type': 'string'
                                },
                                'href': {
                                    'type': 'string',
                                    'pattern': '^/v2/queues/[a-zA-Z0-9_-]+'
                                               '/messages\?(.)*$'
                                }
                            },
                            'required': ['rel', 'href'],
                            'additionalProperties': False
                        }
                    },
                    'messages': {
                        "type": "array",
                        "items": message,
                        "minItems": 0,
                        "maxItems": self.limits.max_messages_per_claim_or_pop
                    }
                }
            },
            'pool_detail': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string'
                    },
                    'uri': {
                        'type': 'string'
                    },
                    'group': {
                        'type': ['string', 'null']
                    },
                    'weight': {
                        'type': 'number',
                        'minimum': -1
                    },
                    'href': {
                        'type': 'string',
                        'pattern': '^/v2/pools/'
                                   '[a-zA-Z0-9_\-]+$'
                    },
                    'options': {
                        'type': 'object',
                        'additionalProperties': True
                    }
                },
                'required': ['uri', 'weight', 'href'],
                'additionalProperties': False
            },

            'claim_create': {
                'type': 'object',
                'properties': {
                    'messages': {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                },
                                "href": claim_href,
                                "ttl": {
                                    "type": "number",
                                    "minimum": 1,
                                    "maximum": self.limits.max_message_ttl
                                },
                                "age": age,
                                "body": {
                                    "type": "object"
                                }
                            },
                            "required": ["href", "ttl", "age", "body", "id"],
                            "additionalProperties": False,
                        },
                        "minItems": 1,
                        "maxItems": self.limits.max_messages_per_page
                    }
                },
                'required': ['messages'],
                'additionalProperties': False
            },

            'claim_get': {
                'type': 'object',
                'properties': {
                    'age': age,
                    'ttl': {
                        'type': 'number',
                        'minimum': 0,
                        'maximum': self.limits.max_claim_ttl
                    },
                    'href': {
                        'type': 'string',
                        'pattern': '^/v2/queues/[a-zA-Z0-9_-]+'
                                   '/claims/[a-zA-Z0-9_-]+$'
                    },
                    'messages': {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                },
                                "href": claim_href,
                                "ttl": {
                                    "type": "number",
                                    "minimum": 1,
                                    "maximum": self.limits.max_message_ttl
                                },
                                "age": age,
                                "body": {
                                    "type": "object"
                                }
                            },
                            "required": ["href", "ttl", "age", "body", "id"],
                            "additionalProperties": False,
                        },
                        "minItems": 1,
                        "maxItems": self.limits.max_messages_per_page
                    }
                },
                'required': ['age', 'ttl', 'messages', 'href'],
                'additionalProperties': False
            },

            'flavor_list': {
                'type': 'object',
                'properties': {
                    'links': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'rel': {
                                    'type': 'string'
                                },
                                'href': {
                                    'type': 'string',
                                    'pattern': '^/v2/flavors\?'
                                }
                            },
                            'required': ['rel', 'href'],
                            'additionalProperties': False
                        }
                    },
                    'flavors': {
                        'type': 'array',
                        'items': flavor,
                    }
                },
                'required': ['links', 'flavors'],
                'additionalProperties': False
            }

        }

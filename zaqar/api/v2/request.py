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

from zaqar.api.v1_1 import request as v1_1


class RequestSchema(v1_1.RequestSchema):

    headers = v1_1.RequestSchema.headers
    schema = v1_1.RequestSchema.schema

    schema.update({

        # Subscriptions
        'subscription_list': {
            'properties': {
                'action': {'enum': ['subscription_list']},
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

        'subscription_create': {
            'properties': {
                'action': {'enum': ['subscription_create']},
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

        'subscription_delete': {
            'properties': {
                'action': {'enum': ['subscription_delete']},
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

        'subscription_get': {
            'properties': {
                'action': {'enum': ['subscription_get']},
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
    })

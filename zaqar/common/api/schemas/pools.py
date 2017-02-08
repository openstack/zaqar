# Copyright (c) 2013 Rackspace Hosting, Inc.
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

"""pools: JSON schema for zaqar-queues pools resources."""

# NOTE(cpp-cabrera): options can be anything. These will be unique to
# each storage driver, so we don't perform any further validation at
# the transport layer.
patch_options = {
    'type': 'object', 'properties': {
        'options': {
            'type': 'object'
        }
    }
}

patch_uri = {
    'type': 'object', 'properties': {
        'uri': {
            'type': 'string',
            'minLength': 0,
            'maxLength': 255,
            'format': 'uri'
        },
        'additionalProperties': False
    }
}

patch_group = {
    'type': 'object', 'properties': {
        'uri': {
            'type': 'string',
            'minLength': 0,
            'maxLength': 255
        },
        'additionalProperties': False
    }
}


patch_weight = {
    'type': 'object', 'properties': {
        'weight': {
            'type': 'integer', 'minimum': 0, 'maximum': 2**32 - 1
        },
        'additionalProperties': False
    }
}

create = {
    'type': 'object', 'properties': {
        'weight': patch_weight['properties']['weight'],
        'group': patch_group['properties']['uri'],
        'uri': patch_uri['properties']['uri'],
        'options': patch_options['properties']['options']
    },
    # NOTE(cpp-cabrera): options need not be present. Storage drivers
    # must provide reasonable defaults.
    'required': ['uri', 'weight'],
    'additionalProperties': False
}

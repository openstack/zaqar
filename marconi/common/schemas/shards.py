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

"""shards: JSON schema for marconi-queues shards resources."""

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

# NOTE(cpp-cabrera): a string valid for use in a URI
# TODO(cpp-cabrera): perhaps validate this further using jsonschema's
# uri validator as per rfc3987
patch_uri = {
    'type': 'object', 'properties': {
        'uri': {
            'type': 'string'
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
        'uri': patch_uri['properties']['uri'],
        'options': patch_options['properties']['options']
    },
    # NOTE(cpp-cabrera): options need not be present. Storage drivers
    # must provide reasonable defaults.
    'required': ['uri', 'weight'],
    'additionalProperties': False
}

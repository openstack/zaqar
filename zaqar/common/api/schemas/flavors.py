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

"""flavors: JSON schema for zaqar-queues flavors resources."""

# NOTE(flaper87): capabilities can be anything. These will be unique to
# each storage driver, so we don't perform any further validation at
# the transport layer.
patch_capabilities = {
    'type': 'object',
    'properties': {
        'capabilities': {
            'type': 'object'
        }
    }
}

# NOTE(gengchc): Add pool_list in flavor creation for removing pool_group
patch_pool_list = {
    'type': 'object',
    'properties': {
        'pool_list': {
            'type': 'array'
        },
        'additionalProperties': False
    }
}

create = {
    'type': 'object',
    'properties': {
        'pool_list': patch_pool_list['properties']['pool_list'],
        'capabilities': patch_capabilities['properties']['capabilities']
    },
    # NOTE(flaper87): capabilities need not be present. Storage drivers
    # must provide reasonable defaults.
    # NOTE(wanghao): remove pool in Newton release.
    'oneOf': [{'required': ['pool_list']}],
    'additionalProperties': False
}

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

create = {
    'type': 'object',
    'properties': {
        'capabilities': patch_capabilities['properties']['capabilities']
    },
    # NOTE(flaper87): capabilities need not be present. Storage drivers
    # must provide reasonable defaults.
    # NOTE(wanghao): remove the whole folder when we remove the 1.1 API
    # totally.
    'additionalProperties': True
}

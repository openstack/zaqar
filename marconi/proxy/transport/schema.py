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

"""schema: JSON Schemas for marconi proxy transports."""

partition_patch_hosts = {
    'type': 'object', 'properties': {
        'hosts': {
            'type': 'array', 'minItems': 1, 'items': {
                'type': 'string'
            }
        },
        'additionalProperties': False
    }
}

partition_patch_weight = {
    'type': 'object', 'properties': {
        'weight': {
            'type': 'integer', 'minimum': 1, 'maximum': 2**32 - 1
        },
        'additionalProperties': False
    }
}

partition_create = {
    'type': 'object', 'properties': {
        'weight': partition_patch_weight['properties']['weight'],
        'hosts': partition_patch_hosts['properties']['hosts']
    },
    'required': ['hosts', 'weight'],
    'additionalProperties': False
}

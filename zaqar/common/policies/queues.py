# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_policy import policy

from zaqar.common.policies import base

QUEUES = 'queues:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=QUEUES % 'get_all',
        check_str=base.UNPROTECTED,
        description='List all message queues.',
        operations=[
            {
                'path': '/v2/queues',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUEUES % 'create',
        check_str=base.UNPROTECTED,
        description='Create a message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}',
                'method': 'PUT'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUEUES % 'get',
        check_str=base.UNPROTECTED,
        description='Get details about a specific message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUEUES % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete a message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUEUES % 'update',
        check_str=base.UNPROTECTED,
        description='Update a message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUEUES % 'stats',
        check_str=base.UNPROTECTED,
        description='Get statistics about a specific message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/stats',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUEUES % 'share',
        check_str=base.UNPROTECTED,
        description='Create a pre-signed URL for a given message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/share',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=QUEUES % 'purge',
        check_str=base.UNPROTECTED,
        description='Purge resources from a particular message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/purge',
                'method': 'POST'
            }
        ]
    )
]


def list_rules():
    return rules

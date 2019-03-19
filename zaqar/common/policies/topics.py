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

TOPICS = 'topics:%s'

rules = [
    policy.DocumentedRuleDefault(
        name=TOPICS % 'get_all',
        check_str=base.UNPROTECTED,
        description='List all topics.',
        operations=[
            {
                'path': '/v2/topics',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=TOPICS % 'create',
        check_str=base.UNPROTECTED,
        description='Create a topic.',
        operations=[
            {
                'path': '/v2/topics/{topic_name}',
                'method': 'PUT'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=TOPICS % 'get',
        check_str=base.UNPROTECTED,
        description='Get details about a specific topic.',
        operations=[
            {
                'path': '/v2/topics/{topic_name}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=TOPICS % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete a topic.',
        operations=[
            {
                'path': '/v2/topics/{topic_name}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=TOPICS % 'update',
        check_str=base.UNPROTECTED,
        description='Update a topic.',
        operations=[
            {
                'path': '/v2/topics/{topic_name}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=TOPICS % 'stats',
        check_str=base.UNPROTECTED,
        description='Get statistics about a specific topic.',
        operations=[
            {
                'path': '/v2/topics/{topic_name}/stats',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=TOPICS % 'purge',
        check_str=base.UNPROTECTED,
        description='Purge resources from a particular topic.',
        operations=[
            {
                'path': '/v2/topic/{topic_name}/purge',
                'method': 'POST'
            }
        ]
    )
]


def list_rules():
    return rules

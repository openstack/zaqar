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

MESSAGES = 'messages:%s'


rules = [
    policy.DocumentedRuleDefault(
        name=MESSAGES % 'get_all',
        check_str=base.UNPROTECTED,
        description='List all message in a message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/messages',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=MESSAGES % 'create',
        check_str=base.UNPROTECTED,
        description='Create a message in a message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/messages',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=MESSAGES % 'get',
        check_str=base.UNPROTECTED,
        description='Retrieve a specific message from a message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/messages/{message_id}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=MESSAGES % 'delete',
        check_str=base.UNPROTECTED,
        description='Delete a specific message from a message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/messages/{message_id}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=MESSAGES % 'delete_all',
        check_str=base.UNPROTECTED,
        description='Delete all messages from a message queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/messages',
                'method': 'DELETE'
            }
        ]
    )
]


def list_rules():
    return rules

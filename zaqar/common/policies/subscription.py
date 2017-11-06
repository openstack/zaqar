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

SUBSCRIPTIONS = 'subscription:%s'


rules = [
    policy.DocumentedRuleDefault(
        name=SUBSCRIPTIONS % 'get_all',
        check_str=base.UNPROTECTED,
        description='Lists a queue subscriptions.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/subscriptions',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=SUBSCRIPTIONS % 'create',
        check_str=base.UNPROTECTED,
        description='Creates a subscription.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/subscriptions',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=SUBSCRIPTIONS % 'get',
        check_str=base.UNPROTECTED,
        description='Shows details for a subscription.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/subscriptions'
                        '/{subscription_id}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=SUBSCRIPTIONS % 'delete',
        check_str=base.UNPROTECTED,
        description='Deletes the specified subscription.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/subscriptions'
                        '/{subscription_id}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=SUBSCRIPTIONS % 'update',
        check_str=base.UNPROTECTED,
        description='Updates a subscription.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/subscriptions'
                        '/{subscription_id}',
                'method': 'PATCH'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=SUBSCRIPTIONS % 'confirm',
        check_str=base.UNPROTECTED,
        description='Confirms a subscription.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/subscriptions'
                        '/{subscription_id}/confirm',
                'method': 'PUT'
            }
        ]
    )
]


def list_rules():
    return rules

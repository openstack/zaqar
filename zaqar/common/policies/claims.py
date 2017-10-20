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

CLAIMS = 'claims:%s'


rules = [
    policy.DocumentedRuleDefault(
        name=CLAIMS % 'create',
        check_str=base.UNPROTECTED,
        description='Claims a set of messages from the specified queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/claims',
                'method': 'POST'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLAIMS % 'get',
        check_str=base.UNPROTECTED,
        description='Queries the specified claim for the specified queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/claims/{claim_id}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLAIMS % 'delete',
        check_str=base.UNPROTECTED,
        description='Releases the specified claim for the specified queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/claims/{claim_id}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=CLAIMS % 'update',
        check_str=base.UNPROTECTED,
        description='Updates the specified claim for the specified queue.',
        operations=[
            {
                'path': '/v2/queues/{queue_name}/claims/{claim_id}',
                'method': 'PATCH'
            }
        ]
    )
]


def list_rules():
    return rules

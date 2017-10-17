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

POOLS = 'pools:%s'


rules = [
    policy.DocumentedRuleDefault(
        name=POOLS % 'get_all',
        check_str=base.ROLE_ADMIN,
        description='Lists pools.',
        operations=[
            {
                'path': '/v2/pools',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POOLS % 'create',
        check_str=base.ROLE_ADMIN,
        description='Creates a pool.',
        operations=[
            {
                'path': '/v2/pools/{pool_name}',
                'method': 'PUT'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POOLS % 'get',
        check_str=base.ROLE_ADMIN,
        description='Shows details for a pool.',
        operations=[
            {
                'path': '/v2/pools/{pool_name}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POOLS % 'delete',
        check_str=base.ROLE_ADMIN,
        description='Delete pool.',
        operations=[
            {
                'path': '/v2/pools/{pool_name}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=POOLS % 'update',
        check_str=base.ROLE_ADMIN,
        description='Update pool.',
        operations=[
            {
                'path': '/v2/pools/{pool_name}',
                'method': 'PATCH'
            }
        ]
    )
]


def list_rules():
    return rules

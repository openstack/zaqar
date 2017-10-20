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

FLAVORS = 'flavors:%s'


rules = [
    policy.DocumentedRuleDefault(
        name=FLAVORS % 'get_all',
        check_str=base.UNPROTECTED,
        description='Lists flavors.',
        operations=[
            {
                'path': '/v2/flavors',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=FLAVORS % 'create',
        check_str=base.ROLE_ADMIN,
        description='Creates a new flavor.',
        operations=[
            {
                'path': '/v2/flavors/{flavor_name}',
                'method': 'PUT'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=FLAVORS % 'get',
        check_str=base.UNPROTECTED,
        description='Shows details for a flavor.',
        operations=[
            {
                'path': '/v2/flavors/{flavor_name}',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=FLAVORS % 'delete',
        check_str=base.ROLE_ADMIN,
        description='Deletes the specified flavor.',
        operations=[
            {
                'path': '/v2/flavors/{flavor_name}',
                'method': 'DELETE'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=FLAVORS % 'update',
        check_str=base.ROLE_ADMIN,
        description='Update flavor.',
        operations=[
            {
                'path': '/v2/flavors/{flavor_name}',
                'method': 'PATCH'
            }
        ]
    )
]


def list_rules():
    return rules

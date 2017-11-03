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

PING = 'ping:%s'
HEALTH = 'health:%s'

rules = [

    policy.DocumentedRuleDefault(
        name=PING % 'get',
        check_str=base.UNPROTECTED,
        description='Simple health check for end user(ping).',
        operations=[
            {
                'path': '/v2/ping',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name=HEALTH % 'get',
        check_str=base.ROLE_ADMIN,
        description='Detailed health check for cloud operator/admin.',
        operations=[
            {
                'path': '/v2/health',
                'method': 'GET'
            }
        ]
    )
]


def list_rules():
    return rules

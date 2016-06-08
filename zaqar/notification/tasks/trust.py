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

import copy
import datetime

from oslo_utils import timeutils

from zaqar.common import auth
from zaqar.notification.tasks import webhook


class TrustTask(webhook.WebhookTask):
    """A webhook using trust authentication.

    This webhook will use the trust stored in the subscription to ask for a
    token, which will then be passed to the notified service.
    """

    def execute(self, subscription, messages, **kwargs):
        subscription = copy.deepcopy(subscription)
        subscriber = subscription['subscriber']

        trust_id = subscription['options']['trust_id']
        token = auth.get_trusted_token(trust_id)

        subscription['subscriber'] = subscriber[6:]
        headers = {'X-Auth-Token': token,
                   'Content-Type': 'application/json'}
        super(TrustTask, self).execute(subscription, messages, headers,
                                       **kwargs)

    def register(self, subscriber, options, ttl, project_id, request_data):
        if 'trust_id' not in options:
            # We have a trust subscriber without a trust ID,
            # create it
            trustor_user_id = request_data.get('X-USER-ID')
            roles = request_data.get('X-ROLES', '')
            if roles:
                roles = roles.split(',')
            else:
                roles = []
            auth_plugin = request_data.get('keystone.token_auth')
            expires_at = None
            if ttl:
                expires_at = timeutils.utcnow() + datetime.timedelta(
                    seconds=ttl)

            trust_id = auth.create_trust_id(
                auth_plugin, trustor_user_id, project_id, roles,
                expires_at)
            options['trust_id'] = trust_id

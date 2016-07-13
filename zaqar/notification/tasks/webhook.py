# Copyright (c) 2015 Catalyst IT Ltd
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

import json
from oslo_log import log as logging
import requests

from zaqar.i18n import _LE

LOG = logging.getLogger(__name__)


class WebhookTask(object):

    def execute(self, subscription, messages, headers=None, **kwargs):
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        headers.update(subscription['options'].get('post_headers', {}))
        try:
            for msg in messages:
                # NOTE(Eva-i): Unfortunately this will add 'queue_name' key to
                # our original messages(dicts) which will be later consumed in
                # the storage controller. It seems safe though.
                msg['queue_name'] = subscription['source']
                if 'post_data' in subscription['options']:
                    data = subscription['options']['post_data']
                    data = data.replace('"$zaqar_message$"', json.dumps(msg))
                else:
                    data = json.dumps(msg)
                requests.post(subscription['subscriber'],
                              data=data,
                              headers=headers)
        except Exception as e:
            LOG.exception(_LE('webhook task got exception: %s.') % str(e))

    def register(self, subscriber, options, ttl, project_id, request_data):
        pass

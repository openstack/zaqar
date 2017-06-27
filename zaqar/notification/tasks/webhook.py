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

import time

import json
from oslo_log import log as logging
import requests

from zaqar.common import consts

LOG = logging.getLogger(__name__)


def _Linear_function(minimum_delay, maximum_delay, times):
    return range(minimum_delay, maximum_delay, times)

RETRY_BACKOFF_FUNCTION_MAP = {'linear': _Linear_function}


class WebhookTask(object):

    def _post_request_success(self, subscriber, data, headers):
        try:
            response = requests.post(subscriber, data=data, headers=headers)
            if response and (response.status_code in range(200, 500)):
                return True
        except Exception as e:
            LOG.exception('post request got exception in retry: %s.', str(e))
        return False

    def _retry_post(self, sub_retry_policy, queue_retry_policy, subscriber,
                    data, headers):
        retry_policy = None
        if sub_retry_policy.get('ignore_subscription_override') or \
           queue_retry_policy.get('ignore_subscription_override'):
            retry_policy = queue_retry_policy or {}
        else:
            retry_policy = sub_retry_policy or queue_retry_policy or {}
        # Immediate Retry Phase
        for retry_with_no_delay in range(
                0, retry_policy.get('retries_with_no_delay',
                                    consts.RETRIES_WITH_NO_DELAY)):
            LOG.debug('Retry with no delay, count: %s', retry_with_no_delay)
            if self._post_request_success(subscriber, data, headers):
                return
        # Pre-Backoff Phase
        for minimum_delay_retry in range(
                0, retry_policy.get('minimum_delay_retries',
                                    consts.MINIMUM_DELAY_RETRIES)):
            LOG.debug('Retry with minimum delay, count: %s',
                      minimum_delay_retry)
            time.sleep(retry_policy.get('minimum_delay', consts.MINIMUM_DELAY))
            if self._post_request_success(subscriber, data, headers):
                return
        # Backoff Phase: Linear retry
        # TODO(wanghao): Now we only support the linear function, we should
        # support more in Queens.
        retry_function = retry_policy.get('retry_backoff_function', 'linear')
        backoff_function = RETRY_BACKOFF_FUNCTION_MAP[retry_function]
        for i in backoff_function(retry_policy.get('minimum_delay',
                                                   consts.MINIMUM_DELAY),
                                  retry_policy.get('maximum_delay',
                                                   consts.MAXIMUM_DELAY),
                                  consts.LINEAR_INTERVAL):
            LOG.debug('Retry with retry_backoff_function, sleep: %s seconds',
                      i)
            time.sleep(i)
            if self._post_request_success(subscriber, data, headers):
                return
        # Post-Backoff Phase
        for maximum_delay_retries in range(
                0, retry_policy.get('maximum_delay_retries',
                                    consts.MAXIMUM_DELA_RETRIES)):
            LOG.debug('Retry with maximum delay, count: %s',
                      maximum_delay_retries)
            time.sleep(retry_policy.get('maximum_delay', consts.MAXIMUM_DELAY))
            if self._post_request_success(subscriber, data, headers):
                return
        LOG.debug('Send request retries are all failed.')

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
                response = requests.post(subscription['subscriber'],
                                         data=data,
                                         headers=headers)
                if response and (response.status_code not in range(200, 500)):
                    LOG.info("Response is %s, begin to retry",
                             response.status_code)
                    self._retry_post(
                        subscription['options'].get('_retry_policy', {}),
                        kwargs.get('queue_retry_policy'),
                        subscription['subscriber'],
                        data, headers)
        except Exception as e:
            LOG.exception('webhook task got exception: %s.', str(e))
            self._retry_post(subscription['options'].get('_retry_policy', {}),
                             kwargs.get('queue_retry_policy'),
                             subscription['subscriber'],
                             data, headers)

    def register(self, subscriber, options, ttl, project_id, request_data):
        pass

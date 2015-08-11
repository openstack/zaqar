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

from stevedore import driver
import uuid

import futurist
from oslo_log import log as logging
from six.moves import urllib_parse
from taskflow import engines
from taskflow.patterns import unordered_flow as uf

LOG = logging.getLogger(__name__)


class NotifierDriver(object):
    """Notifier which is responsible for sending messages to subscribers.

    """

    def __init__(self, *args, **kwargs):
        self.subscription_controller = kwargs.get('subscription_controller')
        try:
            self.executor = futurist.GreenThreadPoolExecutor()
        except RuntimeError:
            # TODO(flwang): Make the max_workers configurable
            self.executor = futurist.ThreadPoolExecutor(max_workers=10)

    def post(self, queue_name, messages, client_uuid, project=None):
        """Send messages to the subscribers."""
        if self.subscription_controller:
            subscribers = self.subscription_controller.list(queue_name,
                                                            project)

            wh_flow = uf.Flow('webhook_notifier_flow')

            for sub in next(subscribers):
                s_type = urllib_parse.urlparse(sub['subscriber']).scheme
                invoke_args = [uuid.uuid4()]
                invoke_kwds = {'inject': {'subscription': sub,
                                          'messages': messages}}

                mgr = driver.DriverManager('zaqar.notification.tasks',
                                           s_type,
                                           invoke_on_load=True,
                                           invoke_args=invoke_args,
                                           invoke_kwds=invoke_kwds)
                wh_flow.add(mgr.driver)

            if wh_flow:
                e = engines.load(wh_flow, executor=self.executor,
                                 engine='parallel')
                e.run()
        else:
            LOG.error('Failed to get subscription controller.')

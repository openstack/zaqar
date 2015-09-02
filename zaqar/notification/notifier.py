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

import futurist
from oslo_log import log as logging
from six.moves import urllib_parse

LOG = logging.getLogger(__name__)


class NotifierDriver(object):
    """Notifier which is responsible for sending messages to subscribers.

    """

    def __init__(self, *args, **kwargs):
        self.subscription_controller = kwargs.get('subscription_controller')
        # TODO(flwang): Make the max_workers configurable
        self.executor = futurist.ThreadPoolExecutor(max_workers=10)

    def post(self, queue_name, messages, client_uuid, project=None):
        """Send messages to the subscribers."""
        if self.subscription_controller:
            subscribers = self.subscription_controller.list(queue_name,
                                                            project)

            for sub in next(subscribers):
                s_type = urllib_parse.urlparse(sub['subscriber']).scheme

                mgr = driver.DriverManager('zaqar.notification.tasks',
                                           s_type,
                                           invoke_on_load=True)
                self.executor.submit(mgr.driver.execute, sub, messages)
        else:
            LOG.error('Failed to get subscription controller.')

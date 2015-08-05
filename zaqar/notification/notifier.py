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

import uuid

import futurist
from oslo_log import log as logging
import six
from taskflow import engines
from taskflow.patterns import unordered_flow as uf
from taskflow import task

from zaqar.notification.task import webhook

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

    def _generate_task(self, subscriber_uri, message):
        task_name = uuid.uuid4()
        # TODO(flwang): Need to work out a better way to make tasks
        s_type = six.moves.urllib_parse.urlparse(subscriber_uri).scheme

        t = task.Task
        if s_type in ('http', 'https'):
            t = webhook.WebhookTask

        return t(task_name, inject={'uri': subscriber_uri, 'message': message})

    def post(self, queue_name, messages, client_uuid, project=None):
        """Send messages to the subscribers."""
        if self.subscription_controller:
            subscribers = self.subscription_controller.list(queue_name,
                                                            project)

            wh_flow = uf.Flow('webhook_notifier_flow')

            for s in list(next(subscribers)):
                for m in messages:
                    wh_flow.add(self._generate_task(s['subscriber'], m))

            if wh_flow:
                e = engines.load(wh_flow, executor=self.executor,
                                 engine='parallel')
                e.run()
        else:
            LOG.error('Failed to get subscription controller.')

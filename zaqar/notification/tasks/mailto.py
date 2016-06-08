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

from email.mime import text
import json
from six.moves import urllib_parse
import subprocess

from oslo_log import log as logging

from zaqar.i18n import _LE

LOG = logging.getLogger(__name__)


class MailtoTask(object):

    def execute(self, subscription, messages, **kwargs):
        subscriber = urllib_parse.urlparse(subscription['subscriber'])
        params = urllib_parse.parse_qs(subscriber.query)
        params = dict((k.lower(), v) for k, v in params.items())
        conf = kwargs.get('conf')
        try:
            for message in messages:
                p = subprocess.Popen(conf.notification.smtp_command.split(' '),
                                     stdin=subprocess.PIPE)
                # NOTE(Eva-i): Unfortunately this will add 'queue_name' key to
                # our original messages(dicts) which will be later consumed in
                # the storage controller. It seems safe though.
                message['queue_name'] = subscription['source']
                msg = text.MIMEText(json.dumps(message))
                msg["to"] = subscriber.path
                msg["from"] = subscription['options'].get('from', '')
                subject_opt = subscription['options'].get('subject', '')
                msg["subject"] = params.get('subject', subject_opt)
                p.communicate(msg.as_string())
        except OSError as err:
            LOG.exception(_LE('Failed to create process for sendmail, '
                              'because %s.') % str(err))
        except Exception as exc:
            LOG.exception(_LE('Failed to send email because %s.') % str(exc))

    def register(self, subscriber, options, ttl, project_id, request_data):
        pass

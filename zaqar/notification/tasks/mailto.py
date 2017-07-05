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

from zaqar.i18n import _
from zaqar.notification.notifier import MessageType

LOG = logging.getLogger(__name__)


class MailtoTask(object):

    def _make_confirm_string(self, conf_n, message, queue_name):
        confirm_url = conf_n.external_confirmation_url
        if confirm_url is None:
            msg = _("Can't make confirmation email body, need a valid "
                    "confirm url.")
            LOG.error(msg)
            raise Exception(msg)
        param_string_signature = '?Signature=' + message.get('URL-Signature',
                                                             '')
        param_string_methods = '&Methods=' + message.get('URL-Methods', '')
        param_string_paths = '&Paths=' + message.get('URL-Paths', '')
        param_string_project = '&Project=' + message.get('X-Project-ID', '')
        param_string_expires = '&Expires=' + message.get('URL-Expires', '')
        param_string_confirm_url = '&Url=' + message.get('WSGISubscribeURL',
                                                         '')
        param_string_queue = '&Queue=' + queue_name
        confirm_url_string = (confirm_url + param_string_signature +
                              param_string_methods + param_string_paths +
                              param_string_project + param_string_expires +
                              param_string_confirm_url + param_string_queue)
        return confirm_url_string

    def _make_confirmation_email(self, body, subscription, message, conf_n):
        queue_name = subscription['source']
        confirm_url = self._make_confirm_string(conf_n, message,
                                                queue_name)
        email_body = ""
        if body is not None:
            email_body = body.format(queue_name, message['X-Project-ID'],
                                     confirm_url)
        return text.MIMEText(email_body)

    def execute(self, subscription, messages, **kwargs):
        subscriber = urllib_parse.urlparse(subscription['subscriber'])
        params = urllib_parse.parse_qs(subscriber.query)
        params = dict((k.lower(), v) for k, v in params.items())
        conf_n = kwargs.get('conf').notification
        try:
            for message in messages:
                p = subprocess.Popen(conf_n.smtp_command.split(' '),
                                     stdin=subprocess.PIPE)
                # Send confirmation email to subscriber.
                if (message.get('Message_Type') ==
                        MessageType.SubscriptionConfirmation.name):
                    content = conf_n.subscription_confirmation_email_template
                    msg = self._make_confirmation_email(content['body'],
                                                        subscription,
                                                        message, conf_n)
                    msg["to"] = subscriber.path
                    msg["from"] = content['sender']
                    msg["subject"] = content['topic']
                elif (message.get('Message_Type') ==
                        MessageType.UnsubscribeConfirmation.name):
                    content = conf_n.unsubscribe_confirmation_email_template
                    msg = self._make_confirmation_email(content['body'],
                                                        subscription,
                                                        message, conf_n)
                    msg["to"] = subscriber.path
                    msg["from"] = content['sender']
                    msg["subject"] = content['topic']
                else:
                    # NOTE(Eva-i): Unfortunately this will add 'queue_name' key
                    # to our original messages(dicts) which will be later
                    # consumed in the storage controller. It seems safe though.
                    message['queue_name'] = subscription['source']
                    msg = text.MIMEText(json.dumps(message))
                    msg["to"] = subscriber.path
                    msg["from"] = subscription['options'].get('from', '')
                    subject_opt = subscription['options'].get('subject', '')
                    msg["subject"] = params.get('subject', subject_opt)
                p.communicate(msg.as_string())
                LOG.debug("Send mail successfully: %s", msg.as_string())
        except OSError as err:
            LOG.exception('Failed to create process for sendmail, '
                          'because %s.', str(err))
        except Exception as exc:
            LOG.exception('Failed to send email because %s.', str(exc))

    def register(self, subscriber, options, ttl, project_id, request_data):
        pass

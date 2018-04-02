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

from oslo_config import cfg


smtp_mode = cfg.StrOpt(
    'smtp_mode', default='third_part',
    choices=('third_part', 'self_local'),
    help='There are two values can be chosen: third_part or '
         'self_local. third_part means Zaqar will use the tools '
         'from config option smtp_commnd. self_local means the '
         'smtp python library will be used.')


smtp_host = cfg.HostAddressOpt(
    'smtp_host',
    help='The host IP for the email system. It should be '
         'set when smtp_mode is set to self_local.')


smtp_port = cfg.PortOpt(
    'smtp_port',
    help='The port for the email system. It should be set when '
         'smtp_mode is set to self_local.')


smtp_user_name = cfg.StrOpt(
    'smtp_user_name',
    help='The user name for the email system to login. It should '
    'be set when smtp_mode is set to self_local.')


smtp_user_password = cfg.StrOpt(
    'smtp_user_password',
    help='The user password for the email system to login. It '
         'should be set when smtp_mode is set to self_local.')


smtp_command = cfg.StrOpt(
    'smtp_command', default='/usr/sbin/sendmail -t -oi',
    help=(
        'The command of smtp to send email. The format is '
        '"command_name arg1 arg2".'))


max_notifier_workers = cfg.IntOpt(
    'max_notifier_workers', default=10,
    help='The max amount of the notification workers.')


require_confirmation = cfg.BoolOpt(
    'require_confirmation', default=False,
    help='Whether the http/https/email subscription need to be confirmed '
         'before notification.')


external_confirmation_url = cfg.StrOpt(
    'external_confirmation_url',
    help='The confirmation page url that will be used in email subscription '
         'confirmation before notification.')


subscription_confirmation_email_template = cfg.DictOpt(
    "subscription_confirmation_email_template",
    default={'topic': 'Zaqar Notification - Subscription '
                      'Confirmation',
             'body': 'You have chosen to subscribe to the '
                     'queue: {0}. This queue belongs to '
                     'project: {1}. '
                     'To confirm this subscription, '
                     'click or visit this link below: {2}',
             'sender': 'Zaqar Notifications '
                       '<no-reply@openstack.org>'},
    help="Defines the set of subscription confirmation email content, "
         "including topic, body and sender. There is a mapping is "
         "{0} -> queue name, {1} ->project id, {2}-> confirm url in body "
         "string. User can use any of the three values. But they can't use "
         "more than three.")


unsubscribe_confirmation_email_template = cfg.DictOpt(
    "unsubscribe_confirmation_email_template",
    default={'topic': 'Zaqar Notification - '
                      'Unsubscribe Confirmation',
             'body': 'You have unsubscribed successfully to the '
                     'queue: {0}. This queue belongs to '
                     'project: {1}. '
                     'To resubscribe this subscription, '
                     'click or visit this link below: {2}',
             'sender': 'Zaqar Notifications '
                       '<no-reply@openstack.org>'},
    help="Defines the set of unsubscribe confirmation email content, "
         "including topic, body and sender. There is a mapping is "
         "{0} -> queue name, {1} ->project id, {2}-> confirm url in body "
         "string. User can use any of the three values. But they can't use "
         "more than three.")


GROUP_NAME = 'notification'
ALL_OPTS = [
    smtp_mode,
    smtp_host,
    smtp_port,
    smtp_user_name,
    smtp_user_password,
    smtp_command,
    max_notifier_workers,
    require_confirmation,
    external_confirmation_url,
    subscription_confirmation_email_template,
    unsubscribe_confirmation_email_template
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}

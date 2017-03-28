# Copyright (c) 2015 Red Hat, Inc.
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


from oslo_config import cfg


_ADMIN_MODE_OPT = cfg.BoolOpt('admin_mode', default=False,
                              help='Activate privileged endpoints.')


_GENERAL_OPTIONS = (
    _ADMIN_MODE_OPT,
    cfg.BoolOpt('pooling', default=False,
                help=('Enable pooling across multiple storage backends. '
                      'If pooling is enabled, the storage driver '
                      'configuration is used to determine where the '
                      'catalogue/control plane data is kept.'),
                deprecated_opts=[cfg.DeprecatedOpt('sharding')]),
    cfg.BoolOpt('unreliable', default=False,
                help='Disable all reliability constraints.'),
    cfg.ListOpt('enable_deprecated_api_versions', default=[],
                item_type=cfg.types.List(item_type=cfg.types.String(
                    choices=('1', '1.1'))),
                help='List of deprecated API versions to enable.'),
)

_DRIVER_OPTIONS = (
    cfg.StrOpt('transport', default='wsgi',
               help='Transport driver to use.'),
    cfg.StrOpt('message_store', default='mongodb',
               deprecated_opts=[cfg.DeprecatedOpt('storage')],
               help='Storage driver to use as the messaging store.'),
    cfg.StrOpt('management_store', default='mongodb',
               help='Storage driver to use as the management store.'),
)

_DRIVER_GROUP = 'drivers'


_SIGNED_URL_OPTIONS = (
    cfg.StrOpt('secret_key',
               help=('Secret key used to encrypt pre-signed URLs.')),
)

_SIGNED_URL_GROUP = 'signed_url'


_NOTIFICATION_OPTIONS = (
    cfg.StrOpt('smtp_command', default='/usr/sbin/sendmail -t -oi',
               help=('The command of smtp to send email. The format is '
                     '"command_name arg1 arg2".')),
    cfg.IntOpt('max_notifier_workers', default=10,
               help='The max amount of the notification workers.'),
    cfg.BoolOpt('require_confirmation', default=False,
                help='Whether the http/https/email subscription need to be '
                     'confirmed before notification.'),
    cfg.StrOpt('external_confirmation_url',
               help='The confirmation page url that will be used in email '
                    'subscription confirmation before notification.'),
    cfg.DictOpt("subscription_confirmation_email_template",
                default={'topic': 'Zaqar Notification - Subscription '
                                  'Confirmation',
                         'body': 'You have chosen to subscribe to the '
                                 'queue: {0}. This queue belongs to '
                                 'project: {1}. '
                                 'To confirm this subscription, '
                                 'click or visit this link below: {2}',
                         'sender': 'Zaqar Notifications '
                                   '<no-reply@openstack.org>'},
                help="Defines the set of subscription confirmation email "
                     "content, including topic, body and sender. There is "
                     "a mapping is {0} -> queue name, {1} ->project id, "
                     "{2}-> confirm url in body string. User can use any of "
                     "the three value. But they can't use more than three."),
    cfg.DictOpt("unsubscribe_confirmation_email_template",
                default={'topic': 'Zaqar Notification - '
                                  'Unsubscribe Confirmation',
                         'body': 'You have unsubscribed successfully to the '
                                 'queue: {0}. This queue belongs to '
                                 'project: {1}. '
                                 'To resubscribe this subscription, '
                                 'click or visit this link below: {2}',
                         'sender': 'Zaqar Notifications '
                                   '<no-reply@openstack.org>'},
                help="Defines the set of unsubscribe confirmation email "
                     "content, including topic, body and sender. There is "
                     "a mapping is {0} -> queue name, {1} ->project id, "
                     "{2}-> confirm url in body string. User can use any of "
                     "the three value. But they can't use more than three."),
)

_NOTIFICATION_GROUP = 'notification'


_PROFILER_OPTIONS = [
    cfg.BoolOpt("trace_wsgi_transport", default=False,
                help="If False doesn't trace any transport requests."
                     "Please note that it doesn't work for websocket now."),
    cfg.BoolOpt("trace_message_store", default=False,
                help="If False doesn't trace any message store requests."),
    cfg.BoolOpt("trace_management_store", default=False,
                help="If False doesn't trace any management store requests.")
]

_PROFILER_GROUP = "profiler"


def _config_options():
    return [(None, _GENERAL_OPTIONS),
            (_DRIVER_GROUP, _DRIVER_OPTIONS),
            (_SIGNED_URL_GROUP, _SIGNED_URL_OPTIONS),
            (_NOTIFICATION_GROUP, _NOTIFICATION_OPTIONS),
            (_PROFILER_GROUP, _PROFILER_OPTIONS)]

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

default_message_ttl = cfg.IntOpt(
    'default_message_ttl', default=3600,
    help='Defines how long a message will be accessible.')


default_message_delay = cfg.IntOpt(
    'default_message_delay', default=0,
    help=('Defines the defautl value for queue delay seconds.'
          'The 0 means the delayed queues feature is close.'))


default_claim_ttl = cfg.IntOpt(
    'default_claim_ttl', default=300,
    help='Defines how long a message will be in claimed state.')


default_claim_grace = cfg.IntOpt(
    'default_claim_grace', default=60,
    help='Defines the message grace period in seconds.')


default_subscription_ttl = cfg.IntOpt(
    'default_subscription_ttl', default=3600,
    help='Defines how long a subscription will be available.')


max_queues_per_page = cfg.IntOpt(
    'max_queues_per_page', default=20,
    deprecated_name='queue_paging_uplimit',
    deprecated_group='limits:transport',
    help='Defines the maximum number of queues per page.')


max_messages_per_page = cfg.IntOpt(
    'max_messages_per_page', default=20,
    deprecated_name='message_paging_uplimit',
    deprecated_group='limits:transport',
    help='Defines the maximum number of messages per page.')


max_subscriptions_per_page = cfg.IntOpt(
    'max_subscriptions_per_page', default=20,
    deprecated_name='subscription_paging_uplimit',
    deprecated_group='limits:transport',
    help='Defines the maximum number of subscriptions per page.')


max_messages_per_claim_or_pop = cfg.IntOpt(
    'max_messages_per_claim_or_pop', default=20,
    deprecated_name='max_messages_per_claim',
    help='The maximum number of messages that can be claimed (OR) '
         'popped in a single request')


max_queue_metadata = cfg.IntOpt(
    'max_queue_metadata', default=64 * 1024,
    deprecated_name='metadata_size_uplimit',
    deprecated_group='limits:transport',
    help='Defines the maximum amount of metadata in a queue.')


max_messages_post_size = cfg.IntOpt(
    'max_messages_post_size', default=256 * 1024,
    deprecated_name='message_size_uplimit',
    deprecated_group='limits:transport',
    deprecated_opts=[cfg.DeprecatedOpt('max_message_size')],
    help='Defines the maximum size of message posts.')


max_message_ttl = cfg.IntOpt(
    'max_message_ttl', default=1209600,
    deprecated_name='message_ttl_max',
    deprecated_group='limits:transport',
    help='Maximum amount of time a message will be available.')


max_message_delay = cfg.IntOpt(
    'max_message_delay', default=900,
    help='Maximum delay seconds for messages can be claimed.')


max_claim_ttl = cfg.IntOpt(
    'max_claim_ttl', default=43200,
    deprecated_name='claim_ttl_max',
    deprecated_group='limits:transport',
    help='Maximum length of a message in claimed state.')


max_claim_grace = cfg.IntOpt(
    'max_claim_grace', default=43200,
    deprecated_name='claim_grace_max',
    deprecated_group='limits:transport',
    help='Defines the maximum message grace period in seconds.')


subscriber_types = cfg.ListOpt(
    'subscriber_types', default=['http', 'https', 'mailto',
                                 'trust+http', 'trust+https'],
    help='Defines supported subscriber types.')


max_flavors_per_page = cfg.IntOpt(
    'max_flavors_per_page', default=20,
    help='Defines the maximum number of flavors per page.')


max_pools_per_page = cfg.IntOpt(
    'max_pools_per_page', default=20,
    help='Defines the maximum number of pools per page.')


client_id_uuid_safe = cfg.StrOpt(
    'client_id_uuid_safe', default='strict', choices=['strict', 'off'],
    help='Defines the format of client id, the value could be '
         '"strict" or "off". "strict" means the format of client id'
         ' must be uuid, "off" means the restriction be removed.')


min_length_client_id = cfg.IntOpt(
    'min_length_client_id', default='10',
    help='Defines the minimum length of client id if remove the '
         'uuid restriction. Default is 10.')


max_length_client_id = cfg.IntOpt(
    'max_length_client_id', default='36',
    help='Defines the maximum length of client id if remove the '
         'uuid restriction. Default is 36.')


message_delete_with_claim_id = cfg.BoolOpt(
    'message_delete_with_claim_id', default=False,
    help='Enable delete messages must be with claim IDS. This will '
         'improve the security of the message avoiding delete messages before'
         ' they are claimed and handled.')

message_encryption_algorithms = cfg.StrOpt(
    'message_encryption_algorithms', default='AES256', choices=['AES256'],
    help='Defines the encryption algorithms of messages, the value could be '
         '"AES256" for now.')

message_encryption_key = cfg.StrOpt(
    'message_encryption_key', default='AES256',
    help='Defines the encryption key of algorithms.')


GROUP_NAME = 'transport'
ALL_OPTS = [
    default_message_ttl,
    default_message_delay,
    default_claim_ttl,
    default_claim_grace,
    default_subscription_ttl,
    max_queues_per_page,
    max_messages_per_page,
    max_subscriptions_per_page,
    max_messages_per_claim_or_pop,
    max_queue_metadata,
    max_messages_post_size,
    max_message_ttl,
    max_message_delay,
    max_claim_ttl,
    max_claim_grace,
    subscriber_types,
    max_flavors_per_page,
    max_pools_per_page,
    client_id_uuid_safe,
    min_length_client_id,
    max_length_client_id,
    message_delete_with_claim_id,
    message_encryption_algorithms,
    message_encryption_key
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}

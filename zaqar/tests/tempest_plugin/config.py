# Copyright (c) 2016 Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from oslo_config import cfg

service_option = cfg.BoolOpt('zaqar',
                             default=True,
                             help="Whether or not Zaqar is expected to be "
                                  "available")

messaging_group = cfg.OptGroup(name='messaging',
                               title='Messaging Service')

MessagingGroup = [
    cfg.StrOpt('catalog_type',
               default='messaging',
               help='Catalog type of the Messaging service.'),
    cfg.IntOpt('max_queues_per_page',
               default=20,
               help='The maximum number of queue records per page when '
                    'listing queues'),
    cfg.IntOpt('max_queue_metadata',
               default=65536,
               help='The maximum metadata size for a queue'),
    cfg.IntOpt('max_messages_per_page',
               default=20,
               help='The maximum number of queue message per page when '
                    'listing (or) posting messages'),
    cfg.IntOpt('max_message_size',
               default=262144,
               help='The maximum size of a message body'),
    cfg.IntOpt('max_messages_per_claim',
               default=20,
               help='The maximum number of messages per claim'),
    cfg.IntOpt('max_message_ttl',
               default=1209600,
               help='The maximum ttl for a message'),
    cfg.IntOpt('max_claim_ttl',
               default=43200,
               help='The maximum ttl for a claim'),
    cfg.IntOpt('max_claim_grace',
               default=43200,
               help='The maximum grace period for a claim'),
]

# Copyright (c) 2014 Rackspace, Inc.
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

conf = cfg.CONF
_CLI_OPTIONS = (
    cfg.IntOpt(
        'producer_processes',
        short='pp',
        default=1,
        help='Number of Producer Processes'),
    cfg.IntOpt(
        'producer_workers',
        short='pw',
        default=10,
        help='Number of Producer Workers'),

    cfg.IntOpt(
        'consumer_processes',
        short='cp',
        default=1,
        help='Number of Consumer Processes'),
    cfg.IntOpt(
        'consumer_workers',
        short='cw',
        default=0,
        help='Number of Consumer Workers'),

    cfg.IntOpt(
        'observer_processes',
        short='op',
        default=1,
        help='Number of Observer Processes'),
    cfg.IntOpt(
        'observer_workers',
        short='ow',
        default=5,
        help='Number of Observer Workers'),

    cfg.BoolOpt('debug', default=True,
                help=('Tag to indicate if print the details of running.')),

    cfg.FloatOpt('api_version', short='api', default='2',
                 help='Zaqar API version to use'),

    cfg.IntOpt('messages_per_claim', short='cno', default=5,
               help=('Number of messages the consumer will attempt to '
                     'claim at a time')),
    cfg.IntOpt('messages_per_list', short='lno', default=5,
               help=('Number of messages the observer will attempt to '
                     'list at a time')),

    cfg.IntOpt('time', short='t', default=5,
               help="Duration of the performance test, in seconds"),

    cfg.StrOpt('server_url', short='s', default='http://localhost:8888'),

    cfg.StrOpt('queue_prefix', short='q', default='ogre-test-queue'),
    cfg.IntOpt('num_queues', short='qno', default=4),

    cfg.StrOpt('messages_path', short='m'),

    cfg.BoolOpt('skip_queue_reset', default=False,
                help=('Do not reset queues before running'
                      'the performance test')),
)
conf.register_cli_opts(_CLI_OPTIONS)

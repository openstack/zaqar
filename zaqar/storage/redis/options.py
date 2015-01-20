# Copyright (c) 2014 Prashanth Raghu.
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

"""Redis storage driver configuration options."""

from oslo_config import cfg

_deprecated_group = 'drivers:storage:redis'
# options common to management and message storage
_COMMON_REDIS_OPTIONS = (
    cfg.StrOpt('uri', default="redis://127.0.0.1:6379",
               deprecated_opts=[cfg.DeprecatedOpt(
                                'uri',
                                group=_deprecated_group), ],
               help=('Redis connection URI, taking one of three forms. '
                     'For a direct connection to a Redis server, use '
                     'the form "redis://host[:port][?options]", where '
                     'port defaults to 6379 if not specified. For an '
                     'HA master-slave Redis cluster using Redis Sentinel, '
                     'use the form "redis://host1[:port1]'
                     '[,host2[:port2],...,hostN[:portN]][?options]", '
                     'where each host specified corresponds to an '
                     'instance of redis-sentinel. In this form, the '
                     'name of the Redis master used in the Sentinel '
                     'configuration must be included in the query '
                     'string as "master=<name>". Finally, to connect '
                     'to a local instance of Redis over a unix socket, '
                     'you may use the form '
                     '"redis:/path/to/redis.sock[?options]". In all '
                     'forms, the "socket_timeout" option may be '
                     'specified in the query string. Its value is '
                     'given in seconds. If not provided, '
                     '"socket_timeout" defaults to 0.1 seconds.')),

    cfg.IntOpt('max_reconnect_attempts', default=10,
               deprecated_opts=[cfg.DeprecatedOpt(
                                'max_reconnect_attempts',
                                group=_deprecated_group), ],
               help=('Maximum number of times to retry an operation that '
                     'failed due to a redis node failover.')),

    cfg.FloatOpt('reconnect_sleep', default=1.0,
                 deprecated_opts=[cfg.DeprecatedOpt(
                                  'reconnect_sleep',
                                  group=_deprecated_group), ],
                 help=('Base sleep interval between attempts to reconnect '
                       'after a redis node failover. '))

)

MANAGEMENT_REDIS_OPTIONS = _COMMON_REDIS_OPTIONS
MESSAGE_REDIS_OPTIONS = _COMMON_REDIS_OPTIONS

MANAGEMENT_REDIS_GROUP = 'drivers:management_store:redis'
MESSAGE_REDIS_GROUP = 'drivers:message_store:redis'


def _config_options():
    return [(MANAGEMENT_REDIS_GROUP, MANAGEMENT_REDIS_OPTIONS),
            (MESSAGE_REDIS_GROUP, MESSAGE_REDIS_OPTIONS)]

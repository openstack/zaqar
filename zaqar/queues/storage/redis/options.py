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

from oslo.config import cfg


REDIS_OPTIONS = (
    cfg.StrOpt('uri', default="redis://127.0.0.1:6379",
               help=('Redis Server URI. Can also use a '
                     'socket file based connector. '
                     'Ex: redis:/tmp/redis.sock')),

    cfg.IntOpt('max_reconnect_attempts', default=10,
               help=('Maximum number of times to retry an operation that '
                     'failed due to a redis node failover.')),

    cfg.FloatOpt('reconnect_sleep', default=1,
                 help=('Base sleep interval between attempts to reconnect '
                       'after a redis node failover. '))

)

REDIS_GROUP = 'drivers:storage:redis'


def _config_options():
    return [(REDIS_GROUP, REDIS_OPTIONS)]

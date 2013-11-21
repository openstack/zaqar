# Copyright (c) 2013 Rackspace Hosting, Inc.
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
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""MongoDB storage driver configuration options."""

from oslo.config import cfg


MONGODB_OPTIONS = [
    cfg.StrOpt('uri', help='Mongodb Connection URI'),

    # Database name
    # TODO(kgriffs): Consider local sharding across DBs to mitigate
    # per-DB locking latency.
    cfg.StrOpt('database', default='marconi', help='Database name'),

    cfg.IntOpt('partitions', default=2,
               help=('Number of databases across which to '
                     'partition message data, in order to '
                     'reduce writer lock %. DO NOT change '
                     'this setting after initial deployment. '
                     'It MUST remain static. Also, you '
                     'should not need a large number of partitions '
                     'to improve performance, esp. if deploying '
                     'MongoDB on SSD storage.')),

    cfg.IntOpt('max_attempts', default=1000,
               help=('Maximum number of times to retry a failed operation.'
                     'Currently only used for retrying a message post.')),

    cfg.FloatOpt('max_retry_sleep', default=0.1,
                 help=('Maximum sleep interval between retries '
                       '(actual sleep time increases linearly '
                       'according to number of attempts performed).')),

    cfg.FloatOpt('max_retry_jitter', default=0.005,
                 help=('Maximum jitter interval, to be added to the '
                       'sleep interval, in order to decrease probability '
                       'that parallel requests will retry at the '
                       'same instant.')),
]

MONGODB_GROUP = 'drivers:storage:mongodb'

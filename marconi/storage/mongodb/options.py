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

from marconi.common import config

OPTIONS = {
    # Connection string
    'uri': None,

    # Database name
    # TODO(kgriffs): Consider local sharding across DBs to mitigate
    # per-DB locking latency.
    'database': 'marconi',

    # Maximum number of times to retry a failed operation. Currently
    # only used for retrying a message post.
    'max_attempts': 1000,

    # Maximum sleep interval between retries (actual sleep time
    # increases linearly according to number of attempts performed).
    'max_retry_sleep': 0.1,

    # Maximum jitter interval, to be added to the sleep interval, in
    # order to decrease probability that parallel requests will retry
    # at the same instant.
    'max_retry_jitter': 0.005,

    # Frequency of message garbage collections, in seconds
    'gc_interval': 5 * 60,

    # Threshold of number of expired messages to reach in a given
    # queue, before performing the GC. Useful for reducing frequent
    # locks on the DB for non-busy queues, or for worker queues
    # which process jobs quickly enough to keep the number of in-
    # flight messages low.
    #
    # Note: The higher this number, the larger the memory-mapped DB
    # files will be.
    'gc_threshold': 1000,
}

CFG = config.namespace('drivers:storage:mongodb').from_options(**OPTIONS)

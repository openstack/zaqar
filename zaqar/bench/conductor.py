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

from __future__ import print_function

import json
import multiprocessing as mp
import os
# NOTE(Eva-i): See https://github.com/gevent/gevent/issues/349. Let's keep
# it until the new stable version of gevent(>=1.1) will be released.
os.environ["GEVENT_RESOLVER"] = "ares"

from zaqar.bench import config
from zaqar.bench import consumer
from zaqar.bench import helpers
from zaqar.bench import observer
from zaqar.bench import producer

CONF = config.conf


def _print_debug_stats(name, stats):
    print(name.capitalize())
    print('=' * len(name))

    values = sorted(stats.items(), key=lambda v: v[0])
    formatted_vals = ['{}: {:.1f}'.format(*v) for v in values]

    print('\n'.join(formatted_vals))
    print()  # Blank line


def _reset_queues():
    cli = helpers.get_new_client()
    for queue_name in helpers.queue_names:
        queue = cli.queue(queue_name)
        queue.delete()


def main():
    CONF(project='zaqar', prog='zaqar-benchmark')

    # NOTE(kgriffs): Reset queues since last time. We don't
    # clean them up after the performance test, in case
    # the user wants to examine the state of the system.
    if not CONF.skip_queue_reset:
        if CONF.debug:
            print('Resetting queues...')

        _reset_queues()

    downstream_queue = mp.Queue()
    procs = [mp.Process(target=worker.run, args=(downstream_queue,))
             for worker in [producer, consumer, observer]]

    for each_proc in procs:
        each_proc.start()

    for each_proc in procs:
        each_proc.join()

    stats = {}
    for each_proc in procs:
        stats.update(downstream_queue.get_nowait())

    if CONF.debug:
        print()

        for name in ('producer', 'observer', 'consumer'):
            stats_group = stats[name]

            # Skip disabled workers
            if not stats_group['duration_sec']:
                continue

            _print_debug_stats(name, stats_group)

    else:
        stats['params'] = {
            'producer': {
                'processes': CONF.producer_processes,
                'workers': CONF.producer_workers
            },
            'consumer': {
                'processes': CONF.consumer_processes,
                'workers': CONF.consumer_workers
            },
            'observer': {
                'processes': CONF.observer_processes,
                'workers': CONF.observer_workers
            },
        }

        print(json.dumps(stats))

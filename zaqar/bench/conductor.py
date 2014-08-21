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

from zaqar.bench.config import conf
from zaqar.bench import consumer
from zaqar.bench import producer


def main():
    downstream_queue = mp.Queue()
    procs = [mp.Process(target=worker.run, args=(downstream_queue,))
             for worker in [producer, consumer]]

    for each_proc in procs:
        each_proc.start()

    for each_proc in procs:
        each_proc.join()

    stats = {}
    for each_proc in procs:
        stats.update(downstream_queue.get_nowait())

    if conf.verbose:
        print()

        for name, stats_group in stats.items():
            print(name.capitalize())
            print('=' * len(name))

            values = sorted(stats_group.items(), key=lambda v: v[0])
            formatted_vals = ["{}: {:.1f}".format(*v) for v in values]

            print("\n".join(formatted_vals))
            print('')  # Blank line

    else:
        stats['params'] = {
            'producer': {
                'processes': conf.producer_processes,
                'workers': conf.producer_workers
            },
            'consumer': {
                'processes': conf.consumer_processes,
                'workers': conf.consumer_workers
            }
        }

        print(json.dumps(stats))

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

from __future__ import division
from __future__ import print_function

import multiprocessing as mp
import sys
import time

from gevent import monkey as curious_george
curious_george.patch_all(thread=False, select=False)
import gevent
import marktime
from zaqarclient.queues.v1 import client
from zaqarclient.transport.errors import TransportError

from zaqar.bench.config import conf


def claim_delete(stats, test_duration, ttl, grace, limit):
    """Consumer Worker

    The Consumer Worker continuously claims and deletes messages
    for the specified duration. The time taken for each claim and
    delete is recorded for calculating throughput and latency.
    """

    cli = client.Client(conf.server_url)
    queue = cli.queue(conf.queue_prefix + '1')
    end = time.time() + test_duration
    total_elapsed = 0
    total_requests = 0
    claim_total_requests = 0
    delete_total_requests = 0

    while time.time() < end:
        marktime.start('claim_message')
        try:
            claim = queue.claim(ttl=ttl, grace=grace, limit=limit)

        except TransportError as ex:
            sys.stderr.write("Could not claim messages : {0}\n".format(ex))

        else:
            total_elapsed += marktime.stop('claim_message').seconds
            claim_total_requests += 1

            try:
                marktime.start('delete_message')

                for msg in claim:
                    # TODO(TheSriram): Simulate actual work before deletion
                    msg.delete()

                total_elapsed += marktime.stop('delete_message').seconds
                delete_total_requests += 1

            except TransportError as ex:
                sys.stderr.write("Could not delete messages: {0}\n".format(ex))

            finally:
                total_requests += 1
        finally:
            total_requests += 1

    stats.put({'total_requests': total_requests,
               'claim_total_requests': claim_total_requests,
               'delete_total_requests': delete_total_requests,
               'total_elapsed': total_elapsed})


def load_generator(stats, num_workers, test_duration, url, ttl, grace, limit):
    gevent.joinall([
        gevent.spawn(claim_delete, stats, test_duration, ttl,
                     grace, limit)
        for _ in range(num_workers)
    ])


def crunch(stats):
    total_requests = 0
    total_latency = 0.0
    claim_total_requests = 0
    delete_total_requests = 0

    while not stats.empty():
        entry = stats.get_nowait()
        total_requests += entry['total_requests']
        total_latency += entry['total_elapsed']
        claim_total_requests += entry['claim_total_requests']
        delete_total_requests += entry['delete_total_requests']

    return (total_requests, total_latency, claim_total_requests,
            delete_total_requests)


def run(upstream_queue):
    num_procs = conf.processes
    num_workers = conf.workers
    test_duration = conf.time
    stats = mp.Queue()
    # TODO(TheSriram) : Make ttl,grace and limit configurable
    args = (stats, num_workers, test_duration, conf.server_url, 300, 200, 1)

    procs = [mp.Process(target=load_generator, args=args)
             for _ in range(num_procs)]

    if conf.verbose:
        print("\nStarting Consumer...")

    start = time.time()

    for each_proc in procs:
        each_proc.start()
    for each_proc in procs:
        each_proc.join()

    (total_requests, total_latency, claim_total_requests,
     delete_total_requests) = crunch(stats)

    successful_requests = claim_total_requests + delete_total_requests
    duration = time.time() - start
    throughput = successful_requests / duration
    latency = 1000 * total_latency / successful_requests

    upstream_queue.put({'consumer': {
        'duration_sec': duration,
        'total_reqs': total_requests,
        'successful_reqs': successful_requests,
        'reqs_per_sec': throughput,
        'ms_per_req': latency}})

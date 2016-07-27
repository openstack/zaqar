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
import random
import sys
import time

from gevent import monkey as curious_george
curious_george.patch_all(thread=False, select=False)
import gevent
import marktime
from zaqarclient.transport import errors

from zaqar.bench import config
from zaqar.bench import helpers

CONF = config.conf


def claim_delete(queues, stats, test_duration, ttl, grace, limit):
    """Consumer Worker

    The Consumer Worker continuously claims and deletes messages
    for the specified duration. The time taken for each claim and
    delete is recorded for calculating throughput and latency.
    """

    end = time.time() + test_duration
    claim_total_elapsed = 0
    delete_total_elapsed = 0
    total_failed_requests = 0
    claim_total_requests = 0
    delete_total_requests = 0

    while time.time() < end:
        # NOTE(kgriffs): Distribute requests across all queues evenly.
        queue = random.choice(queues)

        try:
            marktime.start('claim_message')

            claim = queue.claim(ttl=ttl, grace=grace, limit=limit)

            claim_total_elapsed += marktime.stop('claim_message').seconds
            claim_total_requests += 1

        except errors.TransportError as ex:
            sys.stderr.write("Could not claim messages : {0}\n".format(ex))
            total_failed_requests += 1

        else:
            for msg in claim:
                try:
                    marktime.start('delete_message')

                    msg.delete()

                    elapsed = marktime.stop('delete_message').seconds
                    delete_total_elapsed += elapsed
                    delete_total_requests += 1

                except errors.TransportError as ex:
                    msg = "Could not delete messages: {0}\n".format(ex)
                    sys.stderr.write(msg)
                    total_failed_requests += 1

    total_requests = (claim_total_requests +
                      delete_total_requests +
                      total_failed_requests)

    stats.put({
        'total_requests': total_requests,
        'claim_total_requests': claim_total_requests,
        'delete_total_requests': delete_total_requests,
        'claim_total_elapsed': claim_total_elapsed,
        'delete_total_elapsed': delete_total_elapsed,
    })


def load_generator(stats, num_workers, num_queues,
                   test_duration, url, ttl, grace, limit):

    cli = helpers.get_new_client()
    queues = []
    for queue_name in helpers.queue_names:
        queues.append(cli.queue(queue_name))

    gevent.joinall([
        gevent.spawn(claim_delete,
                     queues, stats, test_duration, ttl, grace, limit)

        for _ in range(num_workers)
    ])


def crunch(stats):
    total_requests = 0
    claim_total_elapsed = 0.0
    delete_total_elapsed = 0.0
    claim_total_requests = 0
    delete_total_requests = 0

    while not stats.empty():
        entry = stats.get_nowait()
        total_requests += entry['total_requests']
        claim_total_elapsed += entry['claim_total_elapsed']
        delete_total_elapsed += entry['delete_total_elapsed']
        claim_total_requests += entry['claim_total_requests']
        delete_total_requests += entry['delete_total_requests']

    return (total_requests, claim_total_elapsed, delete_total_elapsed,
            claim_total_requests, delete_total_requests)


def run(upstream_queue):
    num_procs = CONF.consumer_processes
    num_workers = CONF.consumer_workers
    num_queues = CONF.num_queues

    # Stats that will be reported
    duration = 0
    total_requests = 0
    successful_requests = 0
    claim_total_requests = 0
    delete_total_requests = 0
    throughput = 0
    claim_latency = 0
    delete_latency = 0

    # Performance test
    if num_procs and num_workers:
        stats = mp.Queue()
        # TODO(TheSriram) : Make ttl and grace configurable
        args = (stats, num_workers, num_queues, CONF.time, CONF.server_url,
                300, 200, CONF.messages_per_claim)

        procs = [mp.Process(target=load_generator, args=args)
                 for _ in range(num_procs)]

        if CONF.debug:
            print('\nStarting consumers (cp={0}, cw={1})...'.format(
                  num_procs, num_workers))

        start = time.time()

        for each_proc in procs:
            each_proc.start()

        for each_proc in procs:
            each_proc.join()

        (total_requests, claim_total_elapsed, delete_total_elapsed,
         claim_total_requests, delete_total_requests) = crunch(stats)

        successful_requests = claim_total_requests + delete_total_requests
        duration = time.time() - start

        # NOTE(kgriffs): Duration should never be zero
        throughput = successful_requests / duration

        if claim_total_requests:
            claim_latency = (1000 * claim_total_elapsed /
                             claim_total_requests)

        if delete_total_requests:
            delete_latency = (1000 * delete_total_elapsed /
                              delete_total_requests)

    upstream_queue.put({
        'consumer': {
            'duration_sec': duration,
            'total_reqs': total_requests,
            'claim_total_requests': claim_total_requests,
            'successful_reqs': successful_requests,
            'messages_processed': delete_total_requests,
            'reqs_per_sec': throughput,
            'ms_per_claim': claim_latency,
            'ms_per_delete': delete_latency,
        }
    })

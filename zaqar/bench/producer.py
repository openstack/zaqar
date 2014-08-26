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

import json
import multiprocessing as mp
import random
import sys
import time

from gevent import monkey as curious_george
curious_george.patch_all(thread=False, select=False)
import gevent
import marktime
from zaqarclient.queues.v1 import client
from zaqarclient.transport.errors import TransportError

from zaqar.bench.config import conf


def choose_message(message_pool):
    """Choose a message from our pool of possibilities."""

    # Assume message_pool is sorted by weight, ascending
    position = random.random()
    accumulator = 0.00

    for each_message in message_pool:
        accumulator += each_message['weight']
        if position < accumulator:
            return each_message['doc']

    assert False


def load_messages():
    default_file_name = 'zaqar-benchmark-messages.json'
    messages_path = conf.messages_path or conf.find_file(default_file_name)
    if messages_path:
        with open(messages_path) as f:
            message_pool = json.load(f)
        message_pool.sort(key=lambda msg: msg['weight'])
        return message_pool
    else:
        return [{"weight": 1.0,
                 "doc": {"ttl": 60,
                         "body": {"id": "7FA23C90-62F7-40D2-9360-FBD5D7D61CD1",
                                  "evt": "Single"}}}]


def producer(stats, test_duration):
    """Producer Worker

    The Producer Worker continuously post messages for
    the specified duration. The time taken for each post
    is recorded for calculating throughput and latency.
    """

    cli = client.Client(conf.server_url)
    queue = cli.queue(conf.queue_prefix + '1')
    message_pool = load_messages()

    total_requests = 0
    successful_requests = 0
    total_elapsed = 0
    end = time.time() + test_duration

    while time.time() < end:
        marktime.start('post message')

        # TODO(TheSriram): Track/report errors
        try:
            queue.post(choose_message(message_pool))

        except TransportError as ex:
            sys.stderr.write("Could not post a message : {0}\n".format(ex))

        else:
            successful_requests += 1
            total_elapsed += marktime.stop('post message').seconds

        finally:
            total_requests += 1

    stats.put({
        'successful_requests': successful_requests,
        'total_requests': total_requests,
        'total_elapsed': total_elapsed
    })


# TODO(TheSriram): make distributed across multiple machines
# TODO(TheSriram): post across several queues (which workers to which queues?
# weight them, so can have some busy queues, some not.)
def load_generator(stats, num_workers, test_duration):
    # TODO(TheSriram): Have some way to get all of the workers to line up and
    # start at the same time (is this really useful?)

    gevent.joinall([
        gevent.spawn(producer, stats, test_duration)
        for _ in range(num_workers)
    ])


def crunch(stats):
    total_requests = 0
    total_latency = 0.0
    successful_requests = 0

    while not stats.empty():
        entry = stats.get_nowait()
        total_requests += entry['total_requests']
        total_latency += entry['total_elapsed']
        successful_requests += entry['successful_requests']

    return successful_requests, total_requests, total_latency


def run(upstream_queue):
    num_procs = conf.producer_processes
    num_workers = conf.producer_workers

    duration = 0
    total_requests = 0
    successful_requests = 0
    throughput = 0
    latency = 0

    if num_procs and num_workers:
        test_duration = conf.time
        stats = mp.Queue()
        args = (stats, num_workers, test_duration)

        # TODO(TheSriram): Multiple test runs, vary num workers and
        # drain/delete queues in between each run. Plot these on a
        # graph, with concurrency as the X axis.

        procs = [
            mp.Process(target=load_generator, args=args)
            for _ in range(num_procs)
        ]

        if conf.verbose:
            print('\nStarting Producer...')

        start = time.time()

        for each_proc in procs:
            each_proc.start()

        for each_proc in procs:
            each_proc.join()

        successful_requests, total_requests, total_latency = crunch(stats)

        duration = time.time() - start

        # NOTE(kgriffs): Duration should never be zero
        throughput = successful_requests / duration

        if successful_requests:
            latency = 1000 * total_latency / successful_requests

    upstream_queue.put({
        'producer': {
            'duration_sec': duration,
            'total_reqs': total_requests,
            'successful_reqs': successful_requests,
            'reqs_per_sec': throughput,
            'ms_per_req': latency
        }
    })

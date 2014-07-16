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

import json
import multiprocessing as mp
import os
import random
import sys
import time

from gevent import monkey as curious_george
curious_george.patch_all(thread=False, select=False)
import gevent
from marconiclient.queues.v1 import client
from marconiclient.transport.errors import TransportError
import marktime

from marconi.bench.cli_config import conf


# TODO(TheSriram): Make configurable
URL = 'http://localhost:8888'
QUEUE_PREFIX = 'ogre-test-queue-'

# TODO(TheSriram) : Migrate from env variable to config
if os.environ.get('MESSAGES_PATH'):
    with open(os.environ.get('MESSAGES_PATH')) as f:
        message_pool = json.loads(f.read())
else:
    print("Error : $MESSAGES_PATH needs to be set")
    sys.exit(1)


message_pool.sort(key=lambda msg: msg['weight'])


def choose_message():
    """Choose a message from our pool of possibilities."""

    # Assume message_pool is sorted by weight, ascending
    position = random.random()
    accumulator = 0.00

    for each_message in message_pool:
        accumulator += each_message['weight']
        if position < accumulator:
            return each_message['doc']

    assert False


def producer(stats, test_duration):
    """Producer Worker

    The Producer Worker continuously post messages for
    the specified duration. The time taken for each post
    is recorded for calculating throughput and latency.
    """

    cli = client.Client(URL)
    queue = cli.queue(QUEUE_PREFIX + '1')

    total_requests = 0
    total_elapsed = 0
    end = time.time() + test_duration

    while time.time() < end:
        marktime.start('post message')

        # TODO(TheSriram): Track/report errors
        try:
            queue.post(choose_message())

        except TransportError as ex:
            print("Could not post a message : {0}".format(ex))

        else:
            total_elapsed += marktime.stop('post message').seconds
            total_requests += 1

    stats.put({
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

    while not stats.empty():
        entry = stats.get_nowait()
        total_requests += entry['total_requests']
        total_latency += entry['total_elapsed']

    return total_requests, total_latency


def run():

    num_procs = conf.processes
    num_workers = conf.workers
    test_duration = conf.time
    stats = mp.Queue()
    args = (stats, num_workers, test_duration)

    # TODO(TheSriram): Multiple test runs, vary num workers and drain/delete
    # queues in between each run. Plot these on a graph, with
    # concurrency as the X axis.

    procs = [
        mp.Process(target=load_generator, args=args)
        for _ in range(num_procs)
    ]

    print('\nStarting Producer...')
    start = time.time()

    for each_proc in procs:
        each_proc.start()

    for each_proc in procs:
        each_proc.join()

    total_requests, total_latency = crunch(stats)

    # TODO(TheSriram): Add one more stat: "attempted req/sec" so can
    # graph that on the x axis vs. achieved throughput and
    # latency.
    duration = time.time() - start
    throughput = total_requests / duration
    latency = 1000 * total_latency / total_requests

    print('Duration: {0:.1f} sec'.format(duration))
    print('Total Requests: {0}'.format(total_requests))
    print('Throughput: {0:.0f} req/sec'.format(throughput))
    print('Latency: {0:.1f} ms/req'.format(latency))

    print('')  # Blank line


def main():
    run()

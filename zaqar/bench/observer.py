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
from six.moves import urllib
from zaqarclient.transport import errors

from zaqar.bench import config
from zaqar.bench import helpers

CONF = config.conf


#
# TODO(kgriffs): Factor out the common code from producer, consumer
# and worker (DRY all the things!)
#


def _extract_marker(links):
    for link in links:
        if link['rel'] == 'next':
            href = link['href']
            break

    query = urllib.parse.urlparse(href).query
    params = urllib.parse.parse_qs(query)
    return params['marker'][0]


def observer(queues, stats, test_duration, limit):
    """Observer Worker

    The observer lists messages without claiming them.
    """

    end = time.time() + test_duration

    total_elapsed = 0
    total_succeeded = 0
    total_failed = 0

    queues = [{'q': q, 'm': None} for q in queues]

    while time.time() < end:
        # NOTE(kgriffs): Distribute requests across all queues evenly.
        queue = random.choice(queues)

        try:
            marktime.start('list_messages')
            cursor = queue['q'].messages(limit=limit, marker=queue['m'],
                                         include_claimed=True)
            total_elapsed += marktime.stop('list_messages').seconds
            total_succeeded += 1

            messages = list(cursor)

            if messages:
                # TODO(kgriffs): Figure out a less hacky way to do this
                # while preserving the ability to measure elapsed time
                # per request.
                queue['m'] = _extract_marker(cursor._links)

        except errors.TransportError as ex:
            sys.stderr.write("Could not list messages : {0}\n".format(ex))
            total_failed += 1

    total_requests = total_succeeded + total_failed

    stats.put({
        'total_requests': total_requests,
        'total_succeeded': total_succeeded,
        'total_elapsed': total_elapsed,
    })


def load_generator(stats, num_workers, num_queues,
                   test_duration, limit):

    cli = helpers.get_new_client()
    queues = []
    for queue_name in helpers.queue_names:
        queues.append(cli.queue(queue_name))

    gevent.joinall([
        gevent.spawn(observer,
                     queues, stats, test_duration, limit)

        for _ in range(num_workers)
    ])


def crunch(stats):
    total_requests = 0
    total_succeeded = 0
    total_elapsed = 0.0

    while not stats.empty():
        entry = stats.get_nowait()
        total_requests += entry['total_requests']
        total_succeeded += entry['total_succeeded']
        total_elapsed += entry['total_elapsed']

    return total_requests, total_succeeded, total_elapsed


def run(upstream_queue):
    num_procs = CONF.observer_processes
    num_workers = CONF.observer_workers
    num_queues = CONF.num_queues

    # Stats that will be reported
    duration = 0
    total_requests = 0
    total_succeeded = 0
    throughput = 0
    latency = 0

    # Performance test
    if num_procs and num_workers:
        test_duration = CONF.time
        stats = mp.Queue()
        args = (stats, num_workers, num_queues, test_duration,
                CONF.messages_per_list)

        procs = [mp.Process(target=load_generator, args=args)
                 for _ in range(num_procs)]

        if CONF.debug:
            print('\nStarting observer (op={0}, ow={1})...'.format(
                  num_procs, num_workers))

        start = time.time()

        for each_proc in procs:
            each_proc.start()

        for each_proc in procs:
            each_proc.join()

        (total_requests, total_succeeded, total_elapsed) = crunch(stats)

        duration = time.time() - start

        throughput = total_succeeded / duration

        if total_succeeded:
            latency = (1000 * total_elapsed / total_succeeded)

    upstream_queue.put({
        'observer': {
            'duration_sec': duration,
            'total_reqs': total_requests,
            'successful_reqs': total_succeeded,
            'reqs_per_sec': throughput,
            'ms_per_req': latency,
        }
    })

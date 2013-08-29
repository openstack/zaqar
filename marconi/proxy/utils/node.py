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
# See the License for the specific language governing permissions and
# limitations under the License.
"""node: utilities for implementing partition and node selections."""
import random

import msgpack


def weighted_select(client):
    """Select a partition from all the partitions registered using a weighted
    selection algorithm.

    :raises: RuntimeError if no partitions are registered
    """
    acc = 0
    lookup = []

    # TODO(cpp-cabrera): the lookup table can be constructed once each time
    #                    an entry is added/removed to/from the catalogue,
    #                    rather than each time a queue is created.
    # construct the (partition, weight) lookup table
    for p in client.lrange('ps', 0, -1):
        key = 'p.%s' % p.decode('utf8')
        w = client.hget(key, 'w')
        acc += int(w)
        lookup.append((p.decode('utf8'), acc))

    # select a partition from the lookup table
    selector = random.randint(0, acc - 1)
    last = 0
    for p, w in lookup:
        weight = int(w)
        if selector >= last and selector < weight:
            return p
        last = weight

    raise RuntimeError('No partition could be selected - are any registered?')


def round_robin(client, partition):
    """Select a node in this partition and update the round robin index.

    :returns: the address of a given node
    :side-effect: updates the current index in the storage node for
    this partition
    """
    n, c = client.hmget('p.%s' % partition, ['n', 'c'])
    nodes = [entry.decode('utf8') for entry in msgpack.loads(n)]
    current = int(c)
    client.hset('p.%s' % partition, 'c', (current + 1) % len(nodes))
    return nodes[current]

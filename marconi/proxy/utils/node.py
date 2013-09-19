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


def weighted_select(partitions):
    """Select a partition from all the partitions registered using a weighted
    selection algorithm.

    :param partitions: gen({'name': ..., 'weight': ..., 'hosts': ...}, ...)
    :return: (name, hosts)
    """
    acc = 0
    lookup = []

    # TODO(cpp-cabrera): the lookup table can be constructed once each time
    #                    an entry is added to/removed from the catalogue,
    #                    rather than each time a queue is created.
    # construct the (partition, weight) lookup table
    for p in partitions:
        acc += p['weight']
        lookup.append((p, acc))

    if not lookup:
        return None

    # select a partition from the lookup table
    selector = random.randint(0, acc - 1)
    last = 0
    for p, w in lookup:
        if last <= selector < w:
            return p
        last = w

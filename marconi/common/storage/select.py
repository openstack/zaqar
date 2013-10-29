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

"""select: a collection of algorithms for choosing an entry from a
collection."""

import random


def weighted(objs, key='weight', generator=random.randint):
    """Perform a weighted select given a list of objects.

    :param objs: a list of objects containing at least the field `key`
    :type objs: [dict]
    :param key: the field in each obj that corresponds to weight
    :type key: six.text_type
    :param generator: a number generator taking two ints
    :type generator: function(int, int) -> int
    :return: an object
    :rtype: dict
    """
    acc = 0
    lookup = []

    # construct weighted spectrum
    for o in objs:
        # NOTE(cpp-cabrera): skip objs with 0 weight
        if o[key] <= 0:
            continue
        acc += o[key]
        lookup.append((o, acc))

    # no objects were found
    if not lookup:
        return None

    # NOTE(cpp-cabrera): select an object from the lookup table. If
    # the selector lands in the interval [lower, upper), then choose
    # it.
    gen = generator
    selector = gen(0, acc - 1)
    lower = 0
    for obj, upper in lookup:
        if lower <= selector < upper:
            return obj
        lower = upper

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

"""round_robin: Implements round-robin selection for partition hosts."""

import itertools


class Selector(object):
    def __init__(self):
        self._index = {}

    def next(self, name, hosts):
        """Round robin selection of hosts

        :param name: text - name to associate this list with
        :param hosts: [a] - list of things to round robin. In the context
                            of Marconi, this is a list of URLs.
        """
        if name not in self._index:
            self._index[name] = itertools.cycle(hosts)
        return next(self._index[name])

# Copyright (c) 2013 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import traceback

from marconi import tests as testing


class TestCache(testing.TestBase):

    def test_import(self):
        try:
            from marconi.common.cache._backends import memcached
            from marconi.common.cache._backends import memory
            from marconi.common.cache import backends
            from marconi.common.cache import cache

        except ImportError as ex:
            self.fail(traceback.format_exc(ex))

        # Avoid pyflakes warnings
        cache = cache
        backends = backends
        memory = memory
        memcached = memcached

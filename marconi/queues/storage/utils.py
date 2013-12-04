# Copyright (c) 2013 Rackspace, Inc.
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
#
# See the License for the specific language governing permissions and
# limitations under the License.

from stevedore import driver

from marconi.common import errors
from marconi.openstack.common import log

LOG = log.getLogger(__name__)


def load_storage_driver(conf, cache, control_mode=False):
    """Loads a storage driver and returns it.

    The driver's initializer will be passed conf and cache as
    its positional args.

    :param conf: Configuration instance to use for loading the
        driver. Must include a 'drivers' group.
    :param cache: Cache instance that the driver can (optionally)
        use to reduce latency for some operations.
    :param control_mode: (Default False). Determines which
        driver type to load; if False, the data driver is
        loaded. If True, the control driver is loaded.
    """

    mode = 'control' if control_mode else 'data'
    driver_type = 'marconi.queues.{0}.storage'.format(mode)

    try:
        mgr = driver.DriverManager(driver_type,
                                   conf['drivers'].storage,
                                   invoke_on_load=True,
                                   invoke_args=[conf, cache])

        return mgr.driver

    except RuntimeError as exc:
        LOG.exception(exc)
        raise errors.InvalidDriver(exc)


def keyify(key, iterable):
    """Make an iterator from an iterable of dicts compared with a key.

    :param key: A key exists for all dict inside the iterable object
    :param iterable: The input iterable object
    """

    class Keyed(object):
        def __init__(self, obj):
            self.obj = obj

        def __cmp__(self, other):
            return cmp(self.obj[key], other.obj[key])

        # TODO(zyuan): define magic operators to make py3 work
        #     http://code.activestate.com/recipes/576653/

    for item in iterable:
        yield Keyed(item)

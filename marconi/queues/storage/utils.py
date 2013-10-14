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

from marconi.common import exceptions
from marconi.openstack.common import log

LOG = log.getLogger(__name__)


def load_storage_driver(conf):
    """Loads a storage driver and returns it.

    The driver's initializer will be passed conf as its only arg.

    :param conf: Configuration instance to use for loading the
        driver. Must include a 'queues:drivers' group.
    """

    try:
        mgr = driver.DriverManager('marconi.queues.storage',
                                   conf['queues:drivers'].storage,
                                   invoke_on_load=True,
                                   invoke_args=[conf])
        return mgr.driver

    except RuntimeError as exc:
        LOG.exception(exc)
        raise exceptions.InvalidDriver(exc)

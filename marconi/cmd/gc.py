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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import random
import sys
import time

from marconi import bootstrap
from marconi.common import cli
from marconi.common import config
from marconi.openstack.common import log as logging

PROJECT_CFG = config.project('marconi')
LOG = logging.getLogger(__name__)


@cli.runnable
def run():
    """Entry point to start marconi-gc.

    Operators should run 2-3 instances on different
    boxes for fault-tolerance.

    Note: This call blocks until the process is killed
          or interrupted.
    """

    try:
        info = _('Starting marconi-gc')
        print(info + _('. Use CTRL+C to exit...\n'))
        LOG.info(info)

        boot = bootstrap.Bootstrap(cli_args=sys.argv[1:])
        storage_driver = boot.storage
        gc_interval = storage_driver.gc_interval

        # NOTE(kgriffs): Don't want all garbage collector
        # instances running at the same time (will peg the DB).
        offset = random.random() * gc_interval
        time.sleep(offset)

        while True:
            storage_driver.gc()
            time.sleep(gc_interval)

    except NotImplementedError as ex:
        print('The configured storage driver does not support GC.\n')

        LOG.exception(ex)
        print('')

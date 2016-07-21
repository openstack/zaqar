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

from oslo_config import cfg
from oslo_log import log

from zaqar import bootstrap
from zaqar.common import cli

LOG = log.getLogger(__name__)


# In this first approach it's the responsibility of the operator
# to call the garbage collector manually. Using crontab or a similar
# tool is advised.
@cli.runnable
def run():
    # Use the global CONF instance
    conf = cfg.CONF
    conf(project='zaqar', prog='zaqar-gc')

    server = bootstrap.Bootstrap(conf)

    LOG.debug(u'Calling the garbage collector')
    server.storage.gc()

# Copyright (c) 2013 Red Hat, Inc.
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

"""WSGI App for WSGI Containers

This app should be used by external WSGI
containers. For example:

    $ gunicorn zaqar.transport.wsgi.app:app

NOTE: As for external containers, it is necessary
to put config files in the standard paths. There's
no common way to specify / pass configuration files
to the WSGI app when it is called from other apps.
"""

import threading

from oslo_config import cfg
from oslo_log import log
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts

from zaqar import bootstrap
from zaqar import version

# Use the global CONF instance
CONF = cfg.CONF


def init_application():
    gmr_opts.set_defaults(CONF)
    log.register_options(CONF)
    CONF(project='zaqar', prog='zaqar-queues', args=[])
    log.setup(CONF, 'zaqar')

    gmr.TextGuruMeditation.setup_autorun(version, conf=CONF)

    boot = bootstrap.Bootstrap(CONF)
    CONF.drivers.transport = 'wsgi'
    return boot.transport.app


app = application = None

lock = threading.Lock()
with lock:
    if application is None:
        application = init_application()
        # Keep the old name for compatibility
        app = application

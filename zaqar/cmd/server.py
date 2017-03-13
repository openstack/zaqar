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
import os

from oslo_config import cfg
from oslo_log import log
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts

from zaqar import bootstrap
from zaqar.common import cli
from zaqar.common import configs
from zaqar import version

# NOTE(eggmaster): define command line options for zaqar-server
_CLI_OPTIONS = (
    configs._ADMIN_MODE_OPT,
    cfg.BoolOpt('daemon', default=False,
                help='Run Zaqar server in the background.'),
)


@cli.runnable
def run():
    # Use the global CONF instance
    conf = cfg.CONF
    gmr_opts.set_defaults(conf)
    # NOTE(eggmaster): register command line options for zaqar-server
    conf.register_cli_opts(_CLI_OPTIONS)
    log.register_options(conf)

    # NOTE(jeffrey4l): Overwrite the default vaule for
    # logging_context_format_string. Add project_id into it.
    conf.set_default('logging_context_format_string',
                     '%(asctime)s.%(msecs)03d %(process)d %(levelname)s'
                     ' %(name)s [%(request_id)s %(user_identity)s]'
                     ' [project_id:%(project_id)s] %(message)s')
    conf(project='zaqar', prog='zaqar-server')
    log.setup(conf, 'zaqar')

    gmr.TextGuruMeditation.setup_autorun(version, conf=conf)

    server = bootstrap.Bootstrap(conf)

    # The following code is to daemonize zaqar-server to avoid
    # an issue with wsgiref writing to stdout/stderr when we don't
    # want it to.  This is specifically needed to allow zaqar to
    # run under devstack, but it may also be useful for other scenarios.
    # Open /dev/zero and /dev/null for redirection.
    # Daemonizing zaqar-server is needed *just* when running under devstack
    # and when zaqar is invoked with `daemon` command line option.
    if conf.daemon:
        zerofd = os.open('/dev/zero', os.O_RDONLY)
        nullfd = os.open('/dev/null', os.O_WRONLY)

        # Close the stdthings and reassociate them with a non terminal
        os.dup2(zerofd, 0)
        os.dup2(nullfd, 1)
        os.dup2(nullfd, 2)

        # Detach process context, this requires 2 forks.
        try:
            pid = os.fork()
            if pid > 0:
                os._exit(0)
        except OSError:
            os._exit(1)

        try:
            pid = os.fork()
            if pid > 0:
                os._exit(0)
        except OSError:
            os._exit(2)
    server.run()

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

from __future__ import print_function
import atexit
import functools
import os
import sys
import termios

from marconi.openstack.common.gettextutils import _
from marconi.openstack.common import log as logging


LOG = logging.getLogger(__name__)


def _fail(returncode, ex):
    """Handles terminal errors.

    :param returncode: process return code to pass to sys.exit
    :param ex: the error that occurred
    """

    print(ex, file=sys.stderr)
    LOG.exception(ex)
    sys.exit(returncode)


def _enable_echo(enable):
    """Enables or disables terminal echo.

    :param enable: pass True to enable echo, False to disable
    """
    if not os.isatty(sys.stdin.fileno()):
        # if we are not running in an interactive shell we will get
        # termios.error: (25, 'Inappropriate ioctl for device')
        return

    fd = sys.stdin.fileno()
    new_attr = termios.tcgetattr(fd)
    if enable:
        new_attr[3] |= termios.ECHO
    else:
        new_attr[3] &= ~termios.ECHO

    termios.tcsetattr(fd, termios.TCSANOW, new_attr)


def runnable(func):
    """Entry point wrapper.

    Note: This call blocks until the process is killed
          or interrupted.
    """

    @functools.wraps(func)
    def _wrapper():
        atexit.register(_enable_echo, True)
        _enable_echo(False)

        try:
            logging.setup('marconi')
            func()
        except KeyboardInterrupt:
            LOG.info(_(u'Terminating'))
        except Exception as ex:
            _fail(1, ex)

    return _wrapper

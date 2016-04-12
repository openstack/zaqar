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

"""Middleware for handling authorization and authentication."""

from keystonemiddleware import auth_token
from oslo_log import log


STRATEGIES = {}

LOG = log.getLogger(__name__)


class SignedHeadersAuth(object):

    def __init__(self, app, auth_app):
        self._app = app
        self._auth_app = auth_app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO')
        # NOTE(flwang): The root path of Zaqar service shouldn't require any
        # auth.
        if path == '/':
            return self._app(environ, start_response)

        signature = environ.get('HTTP_URL_SIGNATURE')

        if signature is None or path.startswith('/v1'):
            return self._auth_app(environ, start_response)

        return self._app(environ, start_response)


class KeystoneAuth(object):

    @classmethod
    def install(cls, app, conf):
        """Install Auth check on application."""
        LOG.debug(u'Installing Keystone\'s auth protocol')

        return auth_token.AuthProtocol(app,
                                       conf={"oslo-config-config": conf,
                                             "oslo-config-project": "zaqar"})


STRATEGIES['keystone'] = KeystoneAuth


def strategy(strategy):
    """Returns the Auth Strategy.

    :param strategy: String representing
        the strategy to use
    """
    try:
        return STRATEGIES[strategy]
    except KeyError:
        raise RuntimeError

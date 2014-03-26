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

from keystoneclient.middleware import auth_token

from marconi.openstack.common import log


STRATEGIES = {}

LOG = log.getLogger(__name__)


class KeystoneAuth(object):

    OPT_GROUP_NAME = 'keystone_authtoken'

    @classmethod
    def _register_opts(cls, conf):
        """Register keystoneclient middleware options."""

        if cls.OPT_GROUP_NAME not in conf:
            conf.register_opts(auth_token.opts, group=cls.OPT_GROUP_NAME)
            auth_token.CONF = conf

    @classmethod
    def install(cls, app, conf):
        """Install Auth check on application."""
        LOG.debug(u'Installing Keystone\'s auth protocol')
        cls._register_opts(conf)
        conf = dict(conf.get(cls.OPT_GROUP_NAME))
        return auth_token.AuthProtocol(app, conf=conf)


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

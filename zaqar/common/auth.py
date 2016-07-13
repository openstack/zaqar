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


from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneclient.v3 import client
from oslo_config import cfg


PASSWORD_PLUGIN = 'password'
TRUSTEE_CONF_GROUP = 'trustee'
loading.register_auth_conf_options(cfg.CONF, TRUSTEE_CONF_GROUP)


def _config_options():
    trustee_opts = loading.get_auth_common_conf_options()
    trustee_opts.extend(loading.get_auth_plugin_conf_options(PASSWORD_PLUGIN))
    yield TRUSTEE_CONF_GROUP, trustee_opts


def get_trusted_token(trust_id):
    """Return a Keystone token using the given trust_id."""
    auth_plugin = loading.load_auth_from_conf_options(
        cfg.CONF, TRUSTEE_CONF_GROUP, trust_id=trust_id)

    trust_session = session.Session(auth=auth_plugin)
    return trust_session.auth.get_access(trust_session).auth_token


def _get_admin_session():
    auth_plugin = loading.load_auth_from_conf_options(
        cfg.CONF, TRUSTEE_CONF_GROUP)
    return session.Session(auth=auth_plugin)


def _get_user_client(auth_plugin):
    sess = session.Session(auth=auth_plugin)
    return client.Client(session=sess)


def create_trust_id(auth_plugin, trustor_user_id, trustor_project_id, roles,
                    expires_at):
    """Create a trust with the given user for the configured trustee user."""
    admin_session = _get_admin_session()
    trustee_user_id = admin_session.get_user_id()

    client = _get_user_client(auth_plugin)
    trust = client.trusts.create(trustor_user=trustor_user_id,
                                 trustee_user=trustee_user_id,
                                 project=trustor_project_id,
                                 impersonation=True,
                                 role_names=roles,
                                 expires_at=expires_at)
    return trust.id

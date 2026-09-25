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

# NOTE(Eva-i): Some code was taken from python-zaqarclient.

import os

import openstack.config
from zaqarclient.queues import client

from zaqar.bench import config

CONF = config.conf


def _get_credential_args():
    """Retrieves credential arguments for keystone

    Credentials are either read via os-client-config from the environment
    or from a config file ('clouds.yaml'). Config file variables override those
    from the environment variables.

    devstack produces a clouds.yaml with two named clouds - one named
    'devstack' which has user privs and one named 'devstack-admin' which
    has admin privs. This function will default to getting the credentials from
    environment variables. If not all required credentials present in
    environment variables, it tries to get credentials for 'devstack-admin'
    cloud in clouds.yaml. If no 'devstack-admin' cloud found, it tried to get
    credentials for 'devstack' cloud. If no 'devstack' cloud found, throws
    an error and stops the application.
    """
    os_cfg = openstack.config.OpenStackConfig()

    for cloud_name in (None, 'devstack-admin', 'devstack'):
        try:
            cloud = os_cfg.get_one_cloud(cloud=cloud_name)
            cred_args = cloud.get_auth_args()
        except Exception:
            continue

        required_options = ['username', 'password', 'auth_url']
        if not all(arg in cred_args for arg in required_options):
            continue
        break
    else:
        print("Insufficient amount of credentials found for keystone "
              "authentication. Credentials should reside either in "
              "environment variables or in 'clouds.yaml' file. If "
              "both present, the ones in environment variables will "
              "be preferred. Exiting.")
        raise ValueError("Insuficient credentials")

    print("Using '{}' credentials".format(cloud.name))
    return cred_args


def _generate_client_conf():
    auth_strategy = os.environ.get('OS_AUTH_STRATEGY', 'noauth')

    if auth_strategy == 'keystone':
        args = _get_credential_args()
        conf = {
            'auth_opts': {
                'backend': 'keystone',
                'options': args,
            },
        }
    else:
        conf = {
            'auth_opts': {
                'backend': 'noauth',
                'options': {
                    'os_project_id': 'my-lovely-benchmark',
                },
            },
        }
    print("Using '{}' authentication method".format(conf['auth_opts']
                                                    ['backend']))
    return conf


class LazyAPIVersion:
    def __init__(self):
        self.api_version = None

    @property
    def get(self):
        if self.api_version is None:
            conversion_map = {
                2.0: 2,
            }
            try:
                self.api_version = conversion_map[CONF.api_version]
            except KeyError:
                raise ValueError("Unknown Zaqar API version: '{}'.",
                                 CONF.api_version)
            print("Benchmarking Zaqar API v{}...".format(self.api_version))
        return self.api_version


client_conf = _generate_client_conf()
client_api = LazyAPIVersion()
queue_names = []
for i in range(CONF.num_queues):
    queue_names.append(CONF.queue_prefix + '-' + str(i))


def get_new_client():
    return client.Client(CONF.server_url, client_api.get, conf=client_conf)

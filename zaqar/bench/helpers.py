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
import sys

import os_client_config
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
    os_cfg = os_client_config.OpenStackConfig()

    cloud = os_cfg.get_one_cloud()
    cred_args = cloud.get_auth_args()

    cred_args['insecure'] = cloud.auth.get('insecure')
    cred_args['cacert'] = cloud.auth.get('cacert')
    cred_args['token'] = cloud.auth.get('token')

    required_options = ['username', 'password', 'auth_url', 'project_name']
    if not all(arg in cred_args for arg in required_options):
        try:
            cloud = os_cfg.get_one_cloud(cloud='devstack-admin')
        except Exception:
            try:
                cloud = os_cfg.get_one_cloud(cloud='devstack')
            except Exception:
                print("Insufficient amount of credentials found for keystone "
                      "authentication. Credentials should reside either in "
                      "environment variables or in 'clouds.yaml' file. If "
                      "both present, the ones in environment variables will "
                      "be preferred. Exiting.")
                sys.exit()
        cred_args = cloud.get_auth_args()

    print("Using '{}' credentials".format(cloud.name))
    return cred_args


def _generate_client_conf():
    auth_strategy = os.environ.get('OS_AUTH_STRATEGY', 'noauth')

    if auth_strategy == 'keystone':
        args = _get_credential_args()
        conf = {
            'auth_opts': {
                'backend': 'keystone',
                'options': {
                    'os_username': args.get('username'),
                    'os_password': args.get('password'),
                    'os_project_name': args['project_name'],
                    'os_auth_url': args['auth_url'],
                    'insecure': args.get('insecure'),
                    'cacert': args.get('cacert'),
                    'auth_token': args.get('token')
                },
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
    print("Using '{0}' authentication method".format(conf['auth_opts']
                                                     ['backend']))
    return conf


class LazyAPIVersion(object):
    def __init__(self):
        self.api_version = None

    @property
    def get(self):
        if self.api_version is None:
            conversion_map = {
                1.0: 1,
                1.1: 1.1,
                2.0: 2,
            }
            try:
                self.api_version = conversion_map[CONF.api_version]
            except KeyError:
                print("Unknown Zaqar API version: '{}'. Exiting...".format(
                      CONF.api_version))
                sys.exit()
            print("Benchmarking Zaqar API v{0}...".format(self.api_version))
        return self.api_version


client_conf = _generate_client_conf()
client_api = LazyAPIVersion()
queue_names = []
for i in range(CONF.num_queues):
    queue_names.append((CONF.queue_prefix + '-' + str(i)))


def get_new_client():
    return client.Client(CONF.server_url, client_api.get, conf=client_conf)

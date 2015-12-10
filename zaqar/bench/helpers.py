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

from zaqarclient.queues import client

from zaqar.bench import config

CONF = config.conf

client_conf = {
    'auth_opts': {
        'backend': 'noauth',
        'options': {
            'os_project_id': 'my-lovely-benchmark',
        },
    },
}


def get_new_client():
    return client.Client(CONF.server_url, 1.1, conf=client_conf)

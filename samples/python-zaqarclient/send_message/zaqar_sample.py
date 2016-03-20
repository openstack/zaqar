# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
from zaqarclient.queues.v1 import client

client = client.Client('http://localhost:8888', conf={
    'auth_opts': {
        'options': {
            'client_uuid': '355186cd-d1e8-4108-a3ac-a2183697232a',
            'os_auth_token': '8444886dd9b04a1b87ddb502b508261c',
            'os_auth_url': 'http://localhost:5000/v3.0/',
            'os_project_id': '7530fad032ca431e9dc8ed4a5de5d99c'
        }
    }
}, version=2)

queue = client.queue('SampleQueue')

queue.post([{'body': 'Zaqar Sample'}])

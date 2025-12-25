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

from oslo_config import cfg

from zaqar.common import consts


transport = cfg.StrOpt(
    'transport',
    default=consts.TRANSPORT_WSGI,
    choices=(consts.TRANSPORT_WSGI, consts.TRANSPORT_WEBSOCKET),
    help='Transport driver to use.')


message_store = cfg.StrOpt(
    'message_store', default=consts.MSG_STORE_MONGODB,
    deprecated_opts=[cfg.DeprecatedOpt('storage')],
    help='Storage driver to use as the messaging store.')


management_store = cfg.StrOpt(
    'management_store', default=consts.MGMT_STORE_MONGODB,
    help='Storage driver to use as the management store.')


GROUP_NAME = 'drivers'
ALL_OPTS = [
    transport,
    message_store,
    management_store
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}

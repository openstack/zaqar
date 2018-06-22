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


bind = cfg.HostAddressOpt(
    'bind', default='127.0.0.1',
    help='Address on which the self-hosting server will '
         'listen.')


port = cfg.PortOpt(
    'port', default=9000,
    help='Port on which the self-hosting server will listen.')


external_port = cfg.PortOpt(
    'external-port',
    help='Port on which the service is provided to the user.')


notification_bind = cfg.HostAddressOpt(
    'notification-bind',
    help='Address on which the notification server will '
         'listen.')


notification_port = cfg.PortOpt(
    'notification-port', default=0,
    help='Port on which the notification server will listen.')


GROUP_NAME = 'drivers:transport:websocket'
ALL_OPTS = [
    bind,
    port,
    external_port,
    notification_bind,
    notification_port
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}

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


admin_mode = cfg.BoolOpt(
    'admin_mode', default=False,
    help='Activate privileged endpoints.')


pooling = cfg.BoolOpt(
    'pooling', default=False,
    help=('Enable pooling across multiple storage backends. '
          'If pooling is enabled, the storage driver '
          'configuration is used to determine where the '
          'catalogue/control plane data is kept.'),
    deprecated_opts=[cfg.DeprecatedOpt('sharding')])


unreliable = cfg.BoolOpt(
    'unreliable', default=False,
    help='Disable all reliability constraints.')


enable_deprecated_api_versions = cfg.ListOpt(
    'enable_deprecated_api_versions', default=[],
    item_type=cfg.types.List(item_type=cfg.types.String(choices=('1', '1.1'))),
    help='List of deprecated API versions to enable.')


enable_checksum = cfg.BoolOpt(
    'enable_checksum', default=False,
    help='Enable a checksum for message body. The default value is False.')


auth_strategy = cfg.StrOpt(
    'auth_strategy', default='',
    help=('Backend to use for authentication. '
          'For no auth, keep it empty. '
          'Existing strategies: keystone. '
          'See also the keystone_authtoken section below'))

GROUP_NAME = 'DEFAULT'
ALL_OPTS = [
    admin_mode,
    pooling,
    unreliable,
    enable_deprecated_api_versions,
    enable_checksum,
    auth_strategy
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}

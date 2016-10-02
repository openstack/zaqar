# Copyright (c) 2013 Rackspace Hosting, Inc.
#
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

"""MongoDB storage driver configuration options."""

from oslo_config import cfg

_deprecated_group = 'drivers:storage:mongodb'

# options that are common to both management and message storage
_COMMON_OPTIONS = (

    cfg.StrOpt('ssl_keyfile',
               deprecated_opts=[cfg.DeprecatedOpt(
                                'ssl_keyfile',
                                group=_deprecated_group), ],
               help=('The private keyfile used to identify the local '
                     'connection against mongod. If included with the '
                     '``certifle`` then only the ``ssl_certfile`` '
                     'is needed.')),

    cfg.StrOpt('ssl_certfile',
               deprecated_opts=[cfg.DeprecatedOpt(
                                'ssl_certfile',
                                group=_deprecated_group), ],
               help=('The certificate file used to identify the local '
                     'connection against mongod.')),

    cfg.StrOpt('ssl_cert_reqs', default='CERT_REQUIRED',
               deprecated_opts=[cfg.DeprecatedOpt(
                                'ssl_cert_reqs',
                                group=_deprecated_group), ],
               help=('Specifies whether a certificate is required from '
                     'the other side of the connection, and whether it '
                     'will be validated if provided. It must be one of '
                     'the three values ``CERT_NONE``(certificates ignored), '
                     '``CERT_OPTIONAL``(not required, but validated if '
                     'provided), or ``CERT_REQUIRED``(required and '
                     'validated). If the value of this parameter is not '
                     '``CERT_NONE``, then the ``ssl_ca_cert`` parameter '
                     'must point to a file of CA certificates.')),

    cfg.StrOpt('ssl_ca_certs',
               deprecated_opts=[cfg.DeprecatedOpt(
                                'ssl_ca_certs',
                                group=_deprecated_group), ],
               help=('The ca_certs file contains a set of concatenated '
                     '"certification authority" certificates, which are '
                     'used to validate certificates passed from the other '
                     'end of the connection.')),

    cfg.StrOpt('uri',
               deprecated_opts=[cfg.DeprecatedOpt(
                                'uri',
                                group=_deprecated_group), ],
               help=('Mongodb Connection URI. If ssl connection enabled, '
                     'then ``ssl_keyfile``, ``ssl_certfile``, '
                     '``ssl_cert_reqs``, ``ssl_ca_certs`` need to be set '
                     'accordingly.')),

    cfg.StrOpt('database', default='zaqar',
               deprecated_opts=[cfg.DeprecatedOpt(
                                'database',
                                group=_deprecated_group), ],
               help='Database name.'),

    cfg.IntOpt('max_attempts', min=0, default=1000,
               deprecated_opts=[cfg.DeprecatedOpt(
                                'max_attempts',
                                group=_deprecated_group), ],
               help=('Maximum number of times to retry a failed operation. '
                     'Currently only used for retrying a message post.')),

    cfg.FloatOpt('max_retry_sleep', default=0.1,
                 deprecated_opts=[cfg.DeprecatedOpt(
                                  'max_retry_sleep',
                                  group=_deprecated_group), ],
                 help=('Maximum sleep interval between retries '
                       '(actual sleep time increases linearly '
                       'according to number of attempts performed).')),

    cfg.FloatOpt('max_retry_jitter', default=0.005,
                 deprecated_opts=[cfg.DeprecatedOpt(
                                  'max_retry_jitter',
                                  group=_deprecated_group), ],
                 help=('Maximum jitter interval, to be added to the '
                       'sleep interval, in order to decrease probability '
                       'that parallel requests will retry at the '
                       'same instant.')),

    cfg.IntOpt('max_reconnect_attempts', default=10,
               deprecated_opts=[cfg.DeprecatedOpt(
                                'max_reconnect_attempts',
                                group=_deprecated_group), ],
               help=('Maximum number of times to retry an operation that '
                     'failed due to a primary node failover.')),

    cfg.FloatOpt('reconnect_sleep', default=0.020,
                 deprecated_opts=[cfg.DeprecatedOpt(
                                  'reconnect_sleep',
                                  group=_deprecated_group), ],
                 help=('Base sleep interval between attempts to reconnect '
                       'after a primary node failover. '
                       'The actual sleep time increases exponentially (power '
                       'of 2) each time the operation is retried.')),
)

MANAGEMENT_MONGODB_OPTIONS = _COMMON_OPTIONS
MESSAGE_MONGODB_OPTIONS = _COMMON_OPTIONS + (
    # options used only by message_store
    cfg.IntOpt('partitions', default=2,
               deprecated_opts=[cfg.DeprecatedOpt(
                                'partitions',
                                group=_deprecated_group), ],
               help=('Number of databases across which to '
                     'partition message data, in order to '
                     'reduce writer lock %. DO NOT change '
                     'this setting after initial deployment. '
                     'It MUST remain static. Also, you '
                     'should not need a large number of partitions '
                     'to improve performance, esp. if deploying '
                     'MongoDB on SSD storage.')),
)

MANAGEMENT_MONGODB_GROUP = 'drivers:management_store:mongodb'
MESSAGE_MONGODB_GROUP = 'drivers:message_store:mongodb'


def _config_options():
    """Used by config generators.

    Returns a list of (group-name, oslo_config-options) tuples
    for management and message storage.
    """
    return [(MANAGEMENT_MONGODB_GROUP, MANAGEMENT_MONGODB_OPTIONS),
            (MESSAGE_MONGODB_GROUP, MESSAGE_MONGODB_OPTIONS)]

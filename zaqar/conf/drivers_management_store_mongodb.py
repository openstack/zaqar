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


ssl_keyfile = cfg.StrOpt(
    'ssl_keyfile',
    help='The private keyfile used to identify the local '
         'connection against mongod. If included with '
         'the ``certifle`` then only the ``ssl_certfile``'
         ' is needed.')


ssl_certfile = cfg.StrOpt(
    'ssl_certfile',
    help='The certificate file used to identify the '
         'local connection against mongod.')


ssl_cert_reqs = cfg.StrOpt(
    'ssl_cert_reqs', default='CERT_REQUIRED',
    choices=[
        ('CERT_NONE',
         'Certificates are ignored'),
        ('CERT_OPTIONAL',
         'Certificates are not required, but validated if provided'),
        ('CERT_REQUIRED',
         'Certificates are required and validated')
    ],
    help='Specifies whether a certificate is required '
         'from the other side of the connection, and '
         'whether it will be validated if provided. '
         'If the value of this parameter is not '
         '``CERT_NONE``, then the ``ssl_ca_cert`` '
         'parameter must point to a file of CA '
         'certificates.')


ssl_ca_certs = cfg.StrOpt(
    'ssl_ca_certs',
    help='The ca_certs file contains a set of concatenated '
         '"certification authority" certificates, which are '
         'used to validate certificates passed from the other '
         'end of the connection.')


uri = cfg.StrOpt(
    'uri',
    secret=True,
    help='Mongodb Connection URI. If ssl connection enabled, '
         'then ``ssl_keyfile``, ``ssl_certfile``, '
         '``ssl_cert_reqs``, ``ssl_ca_certs`` need to be set '
         'accordingly.')


database = cfg.StrOpt(
    'database', default='zaqar',
    help='Database name.')

max_attempts = cfg.IntOpt(
    'max_attempts', min=0, default=1000,
    help=('Maximum number of times to retry a failed operation. '
          'Currently only used for retrying a message post.'))


max_retry_sleep = cfg.FloatOpt(
    'max_retry_sleep', default=0.1,
    help=('Maximum sleep interval between retries '
          '(actual sleep time increases linearly '
          'according to number of attempts performed).'))


max_retry_jitter = cfg.FloatOpt(
    'max_retry_jitter', default=0.005,
    help=('Maximum jitter interval, to be added to the '
          'sleep interval, in order to decrease probability '
          'that parallel requests will retry at the '
          'same instant.'))


max_reconnect_attempts = cfg.IntOpt(
    'max_reconnect_attempts', default=10,
    help=('Maximum number of times to retry an operation that '
          'failed due to a primary node failover.'))


reconnect_sleep = cfg.FloatOpt(
    'reconnect_sleep', default=0.020,
    help=('Base sleep interval between attempts to reconnect '
          'after a primary node failover. '
          'The actual sleep time increases exponentially (power '
          'of 2) each time the operation is retried.'))


GROUP_NAME = 'drivers:management_store:mongodb'
ALL_OPTS = [
    ssl_keyfile,
    ssl_certfile,
    ssl_cert_reqs,
    ssl_ca_certs,
    uri,
    database,
    max_attempts,
    max_retry_sleep,
    max_retry_jitter,
    max_reconnect_attempts,
    reconnect_sleep
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}

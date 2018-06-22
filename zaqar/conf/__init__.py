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

import logging

from oslo_cache import core as cache
from oslo_config import cfg
from oslo_log import log

from zaqar.conf import default
from zaqar.conf import drivers
from zaqar.conf import drivers_management_store_mongodb
from zaqar.conf import drivers_management_store_redis
from zaqar.conf import drivers_management_store_sqlalchemy
from zaqar.conf import drivers_message_store_mongodb
from zaqar.conf import drivers_message_store_redis
from zaqar.conf import drivers_message_store_swift
from zaqar.conf import drivers_transport_websocket
from zaqar.conf import drivers_transport_wsgi
from zaqar.conf import notification
from zaqar.conf import pooling_catalog
from zaqar.conf import profiler
from zaqar.conf import signed_url
from zaqar.conf import storage
from zaqar.conf import transport

CONF = cfg.CONF


conf_modules = [
    default,
    drivers,
    drivers_management_store_mongodb,
    drivers_management_store_redis,
    drivers_management_store_sqlalchemy,
    drivers_message_store_mongodb,
    drivers_message_store_redis,
    drivers_message_store_swift,
    drivers_transport_websocket,
    drivers_transport_wsgi,
    notification,
    pooling_catalog,
    profiler,
    signed_url,
    storage,
    transport
]


def setup_logging():
    """Set up logging for the keystone package."""
    log.setup(CONF, 'zaqar')
    logging.captureWarnings(True)


def configure(conf=None):
    if conf is None:
        conf = CONF

    for module in conf_modules:
        module.register_opts(conf)

    # add oslo.cache related config options
    cache.configure(conf)

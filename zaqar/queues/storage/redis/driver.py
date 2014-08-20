# Copyright (c) 2014 Prashanth Raghu.
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

import redis
from six.moves import urllib

from zaqar.common import decorators
from zaqar.openstack.common import log as logging
from zaqar.queues import storage
from zaqar.queues.storage.redis import controllers
from zaqar.queues.storage.redis import options


LOG = logging.getLogger(__name__)


def _get_redis_client(conf):
    # TODO(prashanthr_): Add SSL support
    parsed_url = urllib.parse.urlparse(conf.uri)

    if parsed_url.hostname:
        return redis.StrictRedis(host=parsed_url.hostname,
                                 port=parsed_url.port)
    else:
        return redis.StrictRedis(unix_socket_path=parsed_url.path)


class DataDriver(storage.DataDriverBase):

    def __init__(self, conf, cache):
        super(DataDriver, self).__init__(conf, cache)

        opts = options.REDIS_OPTIONS

        if 'dynamic' in conf:
            names = conf[options.REDIS_GROUP].keys()
            opts = filter(lambda x: x.name not in names, opts)

        self.conf.register_opts(opts,
                                group=options.REDIS_GROUP)
        self.redis_conf = self.conf[options.REDIS_GROUP]

    def is_alive(self):
        try:
            return self.connection.ping()
        except redis.exceptions.ConnectionError:
            return False

    def _health(self):
        KPI = {}
        KPI['storage_reachable'] = self.is_alive()
        KPI['operation_status'] = self._get_operation_status()

        # TODO(kgriffs): Add metrics re message volume
        return KPI

    @decorators.lazy_property(write=False)
    def connection(self):
        """Redis client connection instance."""
        return _get_redis_client(self.redis_conf)

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        return controllers.QueueController(self)

    @decorators.lazy_property(write=False)
    def message_controller(self):
        return controllers.MessageController(self)

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        return controllers.ClaimController(self)


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)

        self.conf.register_opts(options.REDIS_OPTIONS,
                                group=options.REDIS_GROUP)

        self.redis_conf = self.conf[options.REDIS_GROUP]

    @decorators.lazy_property(write=False)
    def connection(self):
        """Redis client connection instance."""
        return _get_redis_client(self.redis_conf)

    @property
    def pools_controller(self):
        return None

    @property
    def catalogue_controller(self):
        return None

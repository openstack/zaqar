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

from osprofiler import profiler
import redis
import redis.sentinel
from six.moves import urllib

from zaqar.common import decorators
from zaqar.common import errors
from zaqar.i18n import _
from zaqar import storage
from zaqar.storage.redis import controllers
from zaqar.storage.redis import options

REDIS_DEFAULT_PORT = 6379
SENTINEL_DEFAULT_PORT = 26379
DEFAULT_SOCKET_TIMEOUT = 0.1

STRATEGY_TCP = 1
STRATEGY_UNIX = 2
STRATEGY_SENTINEL = 3


class ConnectionURI(object):
    def __init__(self, uri):
        # TODO(prashanthr_): Add SSL support
        try:
            parsed_url = urllib.parse.urlparse(uri)
        except SyntaxError:
            raise errors.ConfigurationError(_('Malformed Redis URI'))

        if parsed_url.scheme != 'redis':
            raise errors.ConfigurationError(_('Invalid scheme in Redis URI'))

        # NOTE(kgriffs): Python 2.6 has a bug that causes the
        # query string to be appended to the path when given a
        # hostless URL.
        path = parsed_url.path
        if '?' in path:
            path, sep, query = path.partition('?')
        else:
            query = parsed_url.query

        query_params = dict(urllib.parse.parse_qsl(query))

        # Generic
        self.strategy = None
        self.socket_timeout = float(query_params.get('socket_timeout',
                                                     DEFAULT_SOCKET_TIMEOUT))

        # TCP
        self.port = None
        self.hostname = None

        # UNIX socket
        self.unix_socket_path = None

        # Sentinel
        self.master = None
        self.sentinels = []

        if 'master' in query_params:
            # NOTE(prashanthr_): Configure redis driver in sentinel mode
            self.strategy = STRATEGY_SENTINEL
            self.master = query_params['master']

            # NOTE(kgriffs): Have to parse list of sentinel hosts ourselves
            # since urllib doesn't support it.
            for each_host in parsed_url.netloc.split(','):
                name, sep, port = each_host.partition(':')

                if port:
                    try:
                        port = int(port)
                    except ValueError:
                        msg = _('The Redis configuration URI contains an '
                                'invalid port')
                        raise errors.ConfigurationError(msg)

                else:
                    port = SENTINEL_DEFAULT_PORT

                self.sentinels.append((name, port))

            if not self.sentinels:
                msg = _('The Redis configuration URI does not define any '
                        'sentinel hosts')
                raise errors.ConfigurationError(msg)

        elif parsed_url.netloc:
            if ',' in parsed_url.netloc:
                # NOTE(kgriffs): They probably were specifying
                # a list of sentinel hostnames, but forgot to
                # add 'master' to the query string.
                msg = _('The Redis URI specifies multiple sentinel hosts, '
                        'but is missing the "master" query string '
                        'parameter. Please set "master" to the name of '
                        'the Redis master server as specified in the '
                        'sentinel configuration file.')
                raise errors.ConfigurationError(msg)

            self.strategy = STRATEGY_TCP
            try:
                self.port = parsed_url.port or REDIS_DEFAULT_PORT
            except ValueError:
                msg = _('The Redis configuration URI contains an '
                        'invalid port')
                raise errors.ConfigurationError(msg)

            if not parsed_url.hostname:
                msg = _('Missing host name in Redis URI')
                raise errors.ConfigurationError(msg)

            self.hostname = parsed_url.hostname

        else:
            self.strategy = STRATEGY_UNIX

            if not path:
                msg = _('Missing path in Redis URI')
                raise errors.ConfigurationError(msg)

            self.unix_socket_path = path

        assert self.strategy in (STRATEGY_TCP, STRATEGY_UNIX,
                                 STRATEGY_SENTINEL)


class DataDriver(storage.DataDriverBase):

    # NOTE(flaper87): The driver doesn't guarantee
    # durability for Redis.
    BASE_CAPABILITIES = (storage.Capabilities.FIFO,
                         storage.Capabilities.CLAIMS,
                         storage.Capabilities.AOD,
                         storage.Capabilities.HIGH_THROUGHPUT)

    _DRIVER_OPTIONS = options._config_options()

    def __init__(self, conf, cache, control_driver):
        super(DataDriver, self).__init__(conf, cache, control_driver)
        self.redis_conf = self.conf[options.MESSAGE_REDIS_GROUP]

        server_version = self.connection.info()['redis_version']
        if tuple(map(int, server_version.split('.'))) < (2, 6):
            msg = _('The Redis driver requires redis-server>=2.6, '
                    '%s found') % server_version

            raise RuntimeError(msg)

        # FIXME(flaper87): Make this dynamic
        self._capabilities = self.BASE_CAPABILITIES

    @property
    def capabilities(self):
        return self._capabilities

    def is_alive(self):
        try:
            return self.connection.ping()
        except redis.exceptions.ConnectionError:
            return False

    def close(self):
        self.connection.close()

    def _health(self):
        KPI = {}
        KPI['storage_reachable'] = self.is_alive()
        KPI['operation_status'] = self._get_operation_status()

        # TODO(kgriffs): Add metrics re message volume
        return KPI

    def gc(self):
        # TODO(kgriffs): Check time since last run, and if
        # it hasn't been very long, skip. This allows for
        # running the GC script on multiple boxes for HA,
        # without having them all attempting to GC at the
        # same moment.
        self.message_controller.gc()

    @decorators.lazy_property(write=False)
    def connection(self):
        """Redis client connection instance."""
        return _get_redis_client(self)

    @decorators.lazy_property(write=False)
    def message_controller(self):
        controller = controllers.MessageController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            return profiler.trace_cls("redis_message_controller")(controller)
        else:
            return controller

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        controller = controllers.ClaimController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            return profiler.trace_cls("redis_claim_controller")(controller)
        else:
            return controller

    @decorators.lazy_property(write=False)
    def subscription_controller(self):
        controller = controllers.SubscriptionController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            return profiler.trace_cls("redis_subscription_"
                                      "controller")(controller)
        else:
            return controller


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)

        self.conf.register_opts(options.MANAGEMENT_REDIS_OPTIONS,
                                group=options.MANAGEMENT_REDIS_GROUP)

        self.redis_conf = self.conf[options.MANAGEMENT_REDIS_GROUP]

    def close(self):
        self.connection.close()

    @decorators.lazy_property(write=False)
    def connection(self):
        """Redis client connection instance."""
        return _get_redis_client(self)

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        controller = controllers.QueueController(self)
        if (self.conf.profiler.enabled and
                (self.conf.profiler.trace_message_store or
                    self.conf.profiler.trace_management_store)):
            return profiler.trace_cls("redis_queue_controller")(controller)
        else:
            return controller

    @property
    def pools_controller(self):
        raise NotImplementedError()

    @property
    def catalogue_controller(self):
        raise NotImplementedError()

    @property
    def flavors_controller(self):
        raise NotImplementedError()


def _get_redis_client(driver):
    conf = driver.redis_conf
    connection_uri = ConnectionURI(conf.uri)

    if connection_uri.strategy == STRATEGY_SENTINEL:
        sentinel = redis.sentinel.Sentinel(
            connection_uri.sentinels,
            socket_timeout=connection_uri.socket_timeout)

        # NOTE(prashanthr_): The socket_timeout parameter being generic
        # to all redis connections is inherited from the parameters for
        # sentinel.
        return sentinel.master_for(connection_uri.master)

    elif connection_uri.strategy == STRATEGY_TCP:
        return redis.StrictRedis(
            host=connection_uri.hostname,
            port=connection_uri.port,
            socket_timeout=connection_uri.socket_timeout)
    else:
        return redis.StrictRedis(
            unix_socket_path=connection_uri.unix_socket_path,
            socket_timeout=connection_uri.socket_timeout)

# Copyright (c) 2013 Red Hat, Inc.
#
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

"""Mongodb storage driver implementation."""

import ssl

import pymongo
import pymongo.errors

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar.openstack.common import log as logging
from zaqar import storage
from zaqar.storage.mongodb import controllers
from zaqar.storage.mongodb import options


LOG = logging.getLogger(__name__)


def _connection(conf):
    # NOTE(flaper87): remove possible zaqar specific
    # schemes like: mongodb.fifo
    uri = conf.uri

    if conf.uri:
        uri = "mongodb://%s" % (conf.uri.split("://")[-1])

    if conf.uri and 'replicaSet' in conf.uri:
        MongoClient = pymongo.MongoReplicaSetClient
    else:
        MongoClient = pymongo.MongoClient

    if conf.uri and 'ssl=true' in conf.uri.lower():
        kwargs = {}

        # Default to CERT_REQUIRED
        ssl_cert_reqs = ssl.CERT_REQUIRED

        if conf.ssl_cert_reqs == 'CERT_OPTIONAL':
            ssl_cert_reqs = ssl.CERT_OPTIONAL

        if conf.ssl_cert_reqs == 'CERT_NONE':
            ssl_cert_reqs = ssl.CERT_NONE

        kwargs['ssl_cert_reqs'] = ssl_cert_reqs

        if conf.ssl_keyfile:
            kwargs['ssl_keyfile'] = conf.ssl_keyfile
        if conf.ssl_certfile:
            kwargs['ssl_certfile'] = conf.ssl_certfile
        if conf.ssl_ca_certs:
            kwargs['ssl_ca_certs'] = conf.ssl_ca_certs

        return MongoClient(uri, **kwargs)

    return MongoClient(uri)


class DataDriver(storage.DataDriverBase):

    BASE_CAPABILITIES = tuple(storage.Capabilities)

    _DRIVER_OPTIONS = options._config_options()

    _COL_SUFIX = "_messages_p"

    def __init__(self, conf, cache, control_driver):
        super(DataDriver, self).__init__(conf, cache, control_driver)

        self.mongodb_conf = self.conf[options.MESSAGE_MONGODB_GROUP]

        conn = self.connection
        server_version = conn.server_info()['version']

        if tuple(map(int, server_version.split('.'))) < (2, 2):
            raise RuntimeError(_('The mongodb driver requires mongodb>=2.2,  '
                                 '%s found') % server_version)

        if not len(conn.nodes) > 1 and not conn.is_mongos:
            if not self.conf.unreliable:
                raise RuntimeError(_('Either a replica set or a mongos is '
                                     'required to guarantee message delivery'))
        else:
            wc = conn.write_concern.get('w')
            majority = (wc == 'majority' or
                        wc >= 2)

            if not wc:
                # NOTE(flaper87): No write concern specified, use majority
                # and don't count journal as a replica. Use `update` to avoid
                # overwriting `wtimeout`
                conn.write_concern.update({'w': 'majority'})
            elif not self.conf.unreliable and not majority:
                raise RuntimeError(_('Using a write concern other than '
                                     '`majority` or > 2 makes the service '
                                     'unreliable. Please use a different '
                                     'write concern or set `unreliable` '
                                     'to True in the config file.'))

            conn.write_concern['j'] = False

        # FIXME(flaper87): Make this dynamic
        self._capabilities = self.BASE_CAPABILITIES

    @property
    def capabilities(self):
        return self._capabilities

    def is_alive(self):
        try:
            # NOTE(zyuan): Requires admin access to mongodb
            return 'ok' in self.connection.admin.command('ping')

        except pymongo.errors.PyMongoError:
            return False

    def _health(self):
        KPI = {}
        KPI['storage_reachable'] = self.is_alive()
        KPI['operation_status'] = self._get_operation_status()
        message_volume = {'free': 0, 'claimed': 0, 'total': 0}

        for msg_col in [db.messages for db in self.message_databases]:
            msg_count_claimed = msg_col.find({'c.id': {'$ne': None}}).count()
            message_volume['claimed'] += msg_count_claimed

            msg_count_total = msg_col.find().count()
            message_volume['total'] += msg_count_total

        message_volume['free'] = (message_volume['total'] -
                                  message_volume['claimed'])
        KPI['message_volume'] = message_volume
        return KPI

    @decorators.lazy_property(write=False)
    def message_databases(self):
        """List of message databases, ordered by partition number."""

        name = self.mongodb_conf.database
        partitions = self.mongodb_conf.partitions

        # NOTE(kgriffs): Partition names are zero-based, and
        # the list is ordered by partition, which means that a
        # caller can, e.g., get zaqar_mp0 by simply indexing
        # the first element in the list of databases:
        #
        #     self.driver.message_databases[0]
        #
        return [self.connection[name + self._COL_SUFIX + str(p)]
                for p in range(partitions)]

    @decorators.lazy_property(write=False)
    def subscriptions_database(self):
        """Database dedicated to the "subscription" collection."""
        name = self.mongodb_conf.database + '_subscriptions'
        return self.connection[name]

    @decorators.lazy_property(write=False)
    def connection(self):
        """MongoDB client connection instance."""
        return _connection(self.mongodb_conf)

    @decorators.lazy_property(write=False)
    def message_controller(self):
        return controllers.MessageController(self)

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        return controllers.ClaimController(self)

    @decorators.lazy_property(write=False)
    def subscription_controller(self):
        return controllers.SubscriptionController(self)


class FIFODataDriver(DataDriver):

    BASE_CAPABILITIES = (storage.Capabilities.DURABILITY,
                         storage.Capabilities.CLAIMS,
                         storage.Capabilities.AOD,
                         storage.Capabilities.HIGH_THROUGHPUT)

    _COL_SUFIX = "_messages_fifo_p"

    @decorators.lazy_property(write=False)
    def message_controller(self):
        return controllers.FIFOMessageController(self)


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)

        self.conf.register_opts(options.MANAGEMENT_MONGODB_OPTIONS,
                                group=options.MANAGEMENT_MONGODB_GROUP)

        self.mongodb_conf = self.conf[options.MANAGEMENT_MONGODB_GROUP]

    @decorators.lazy_property(write=False)
    def connection(self):
        """MongoDB client connection instance."""
        return _connection(self.mongodb_conf)

    @decorators.lazy_property(write=False)
    def database(self):
        name = self.mongodb_conf.database
        return self.connection[name]

    @decorators.lazy_property(write=False)
    def queues_database(self):
        """Database dedicated to the "queues" collection.

        The queues collection is separated out into its own database
        to avoid writer lock contention with the messages collections.
        """

        name = self.mongodb_conf.database + '_queues'
        return self.connection[name]

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        return controllers.QueueController(self)

    @property
    def pools_controller(self):
        return controllers.PoolsController(self)

    @property
    def catalogue_controller(self):
        return controllers.CatalogueController(self)

    @property
    def flavors_controller(self):
        return controllers.FlavorsController(self)

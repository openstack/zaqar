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

from osprofiler import profiler
import pymongo
import pymongo.errors

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar import storage
from zaqar.storage.mongodb import controllers
from zaqar.storage.mongodb import options


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
        kwargs = {'connect': False}

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

    return MongoClient(uri, connect=False)


class DataDriver(storage.DataDriverBase):

    BASE_CAPABILITIES = tuple(storage.Capabilities)

    _DRIVER_OPTIONS = options._config_options()

    _COL_SUFIX = "_messages_p"

    def __init__(self, conf, cache, control_driver):
        super(DataDriver, self).__init__(conf, cache, control_driver)

        self.mongodb_conf = self.conf[options.MESSAGE_MONGODB_GROUP]

        conn = self.connection
        server_info = conn.server_info()['version']
        self.server_version = tuple(map(int, server_info.split('.')))

        if self.server_version < (2, 2):
            raise RuntimeError(_('The mongodb driver requires mongodb>=2.2, '
                                 '%s found') % server_info)

        if not len(conn.nodes) > 1 and not conn.is_mongos:
            if not self.conf.unreliable:
                raise RuntimeError(_('Either a replica set or a mongos is '
                                     'required to guarantee message delivery'))
        else:

            _mongo_wc = conn.write_concern.document.get('w')
            # NOTE(flwang): mongo client is using None as the default value of
            # write concern. But in Python 3.x we can't compare by order
            # different types of operands like in Python 2.x.
            # And we can't set the write concern value when create the
            # connection since it will fail with norepl if mongodb version
            # below 2.6. Besides it doesn't make sense to create the
            # connection again after getting the version.
            durable = (_mongo_wc is not None and
                       (_mongo_wc == 'majority' or _mongo_wc >= 2)
                       )

            if not self.conf.unreliable and not durable:
                raise RuntimeError(_('Using a write concern other than '
                                     '`majority` or > 2 makes the service '
                                     'unreliable. Please use a different '
                                     'write concern or set `unreliable` '
                                     'to True in the config file.'))

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

    def close(self):
        self.connection.close()

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

        kwargs = {}
        if not self.server_version < (2, 6):
            # NOTE(flaper87): Skip mongodb versions below 2.6 when
            # setting the write concern on the database. pymongo 3.0
            # fails with norepl when creating indexes.
            doc = self.connection.write_concern.document.copy()
            doc.setdefault('w', 'majority')
            doc.setdefault('j', False)
            kwargs['write_concern'] = pymongo.WriteConcern(**doc)

        name = self.mongodb_conf.database
        partitions = self.mongodb_conf.partitions

        databases = []
        for p in range(partitions):
            db_name = name + self._COL_SUFIX + str(p)
            databases.append(self.connection.get_database(db_name, **kwargs))
        return databases

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
        controller = controllers.MessageController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            return profiler.trace_cls("mongodb_message_controller")(controller)
        else:
            return controller

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        controller = controllers.ClaimController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            return profiler.trace_cls("mongodb_claim_controller")(controller)
        else:
            return controller

    @decorators.lazy_property(write=False)
    def subscription_controller(self):
        controller = controllers.SubscriptionController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            return profiler.trace_cls("mongodb_subscription_"
                                      "controller")(controller)
        else:
            return controller


class FIFODataDriver(DataDriver):

    BASE_CAPABILITIES = (storage.Capabilities.DURABILITY,
                         storage.Capabilities.CLAIMS,
                         storage.Capabilities.AOD,
                         storage.Capabilities.HIGH_THROUGHPUT)

    _COL_SUFIX = "_messages_fifo_p"

    @decorators.lazy_property(write=False)
    def message_controller(self):
        controller = controllers.FIFOMessageController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            return profiler.trace_cls("mongodb_message_controller")(controller)
        else:
            return controller


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)

        self.conf.register_opts(options.MANAGEMENT_MONGODB_OPTIONS,
                                group=options.MANAGEMENT_MONGODB_GROUP)

        self.mongodb_conf = self.conf[options.MANAGEMENT_MONGODB_GROUP]

    def close(self):
        self.connection.close()

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
        controller = controllers.QueueController(self)
        if (self.conf.profiler.enabled and
                (self.conf.profiler.trace_message_store or
                    self.conf.profiler.trace_management_store)):
            return profiler.trace_cls("mongodb_queues_controller")(controller)
        else:
            return controller

    @property
    def pools_controller(self):
        controller = controllers.PoolsController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_management_store):
            return profiler.trace_cls("mongodb_pools_controller")(controller)
        else:
            return controller

    @property
    def catalogue_controller(self):
        controller = controllers.CatalogueController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_management_store):
            return profiler.trace_cls("mongodb_catalogue_"
                                      "controller")(controller)
        else:
            return controller

    @property
    def flavors_controller(self):
        controller = controllers.FlavorsController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_management_store):
            return profiler.trace_cls("mongodb_flavors_controller")(controller)
        else:
            return controller

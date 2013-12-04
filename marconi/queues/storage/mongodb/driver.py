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

import pymongo
import pymongo.errors

from marconi.common import decorators
from marconi.openstack.common import log as logging
from marconi.queues import storage
from marconi.queues.storage.mongodb import controllers
from marconi.queues.storage.mongodb import options


LOG = logging.getLogger(__name__)


def _connection(conf):
    if conf.uri and 'replicaSet' in conf.uri:
        MongoClient = pymongo.MongoReplicaSetClient
    else:
        MongoClient = pymongo.MongoClient

    return MongoClient(conf.uri)


class DataDriver(storage.DataDriverBase):

    def __init__(self, conf, cache):
        super(DataDriver, self).__init__(conf, cache)

        opts = options.MONGODB_OPTIONS

        # NOTE(cpp-cabrera): if this data driver is being loaded
        # dynamically, as would be the case for a sharded context,
        # filter out the options that were given by the shard
        # catalogue to avoid DuplicateOptErrors.
        if 'dynamic' in conf:
            names = conf[options.MONGODB_GROUP].keys()
            opts = filter(lambda x: x.name not in names, opts)

        self.conf.register_opts(opts,
                                group=options.MONGODB_GROUP)
        self.mongodb_conf = self.conf[options.MONGODB_GROUP]

    def is_alive(self):
        try:
            # NOTE(zyuan): Requires admin access to mongodb
            return 'ok' in self.connection.admin.command('ping')

        except pymongo.errors.PyMongoError:
            return False

    @decorators.lazy_property(write=False)
    def queues_database(self):
        """Database dedicated to the "queues" collection.

        The queues collection is separated out into its own database
        to avoid writer lock contention with the messages collections.
        """

        name = self.mongodb_conf.database + '_queues'
        return self.connection[name]

    @decorators.lazy_property(write=False)
    def message_databases(self):
        """List of message databases, ordered by partition number."""

        name = self.mongodb_conf.database
        partitions = self.mongodb_conf.partitions

        # NOTE(kgriffs): Partition names are zero-based, and
        # the list is ordered by partition, which means that a
        # caller can, e.g., get marconi_mp0 by simply indexing
        # the first element in the list of databases:
        #
        #     self.driver.message_databases[0]
        #
        return [self.connection[name + '_messages_p' + str(p)]
                for p in range(partitions)]

    @decorators.lazy_property(write=False)
    def connection(self):
        """MongoDB client connection instance."""
        return _connection(self.mongodb_conf)

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

        self.conf.register_opts(options.MONGODB_OPTIONS,
                                group=options.MONGODB_GROUP)

        self.mongodb_conf = self.conf[options.MONGODB_GROUP]

    @decorators.lazy_property(write=False)
    def connection(self):
        """MongoDB client connection instance."""
        return _connection(self.mongodb_conf)

    @decorators.lazy_property(write=False)
    def shards_database(self):
        name = self.mongodb_conf.database + '_shards'
        return self.connection[name]

    @property
    def shards_controller(self):
        return controllers.ShardsController(self)

    @decorators.lazy_property(write=False)
    def catalogue_database(self):
        """Database dedicated to the "queues" collection.

        The queues collection is separated out into its own database
        to avoid writer lock contention with the messages collections.
        """

        name = self.mongodb_conf.database + '_catalogue'
        return self.connection[name]

    @property
    def catalogue_controller(self):
        return controllers.CatalogueController(self)

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


class Driver(storage.DriverBase):

    @decorators.lazy_property()
    def queues_database(self):
        """Database dedicated to the "queues" collection.

        The queues collection is separated out into it's own database
        to avoid writer lock contention with the messages collections.
        """

        name = options.CFG.database + '_queues'
        return self.connection[name]

    @decorators.lazy_property()
    def message_databases(self):
        """List of message databases, ordered by partition number."""

        name = options.CFG.database
        partitions = options.CFG.partitions

        # NOTE(kgriffs): Partition names are zero-based, and
        # the list is ordered by partition, which means that a
        # caller can, e.g., get marconi_mp0 by simply indexing
        # the first element in the list of databases:
        #
        #     self.driver.message_databases[0]
        #
        return [self.connection[name + '_messages_p' + str(p)]
                for p in range(partitions)]

    @decorators.lazy_property()
    def connection(self):
        """MongoDB client connection instance."""

        if options.CFG.uri and 'replicaSet' in options.CFG.uri:
            MongoClient = pymongo.MongoReplicaSetClient
        else:
            MongoClient = pymongo.MongoClient

        return MongoClient(options.CFG.uri)

    @property
    def gc_interval(self):
        return options.CFG.gc_interval

    @property
    def _queue_controller(self):
        return controllers.QueueController(self)

    @property
    def _message_controller(self):
        return controllers.MessageController(self)

    @property
    def _claim_controller(self):
        return controllers.ClaimController(self)

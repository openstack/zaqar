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

from marconi.openstack.common import log as logging
from marconi import storage
from marconi.storage.mongodb import controllers
from marconi.storage.mongodb import options

LOG = logging.getLogger(__name__)


class Driver(storage.DriverBase):

    def __init__(self):
        # Lazy instantiation
        self._database = None

    @property
    def db(self):
        """Property for lazy instantiation of mongodb's database."""
        if self._database is None:
            if options.CFG.uri and 'replicaSet' in options.CFG.uri:
                conn = pymongo.MongoReplicaSetClient(options.CFG.uri)
            else:
                conn = pymongo.MongoClient(options.CFG.uri)

            self._database = conn[options.CFG.database]

        return self._database

    def gc(self):
        LOG.info('Performing garbage collection.')

        try:
            self.message_controller.remove_expired()
        except pymongo.errors.ConnectionFailure as ex:
            # Better luck next time...
            LOG.exception(ex)

    @property
    def gc_interval(self):
        return options.CFG.gc_interval

    @property
    def queue_controller(self):
        return controllers.QueueController(self)

    @property
    def message_controller(self):
        return controllers.MessageController(self)

    @property
    def claim_controller(self):
        return controllers.ClaimController(self)

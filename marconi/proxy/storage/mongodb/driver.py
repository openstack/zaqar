# Copyright (c) 2013 Rackspace Hosting, Inc.
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

"""Mongodb proxy storage driver implementation."""

import pymongo
import pymongo.errors

from marconi.openstack.common import log as logging
from marconi.proxy import storage
from marconi.proxy.storage.mongodb import controllers
from marconi.proxy.storage.mongodb import options


LOG = logging.getLogger(__name__)


class Driver(storage.DriverBase):

    def __init__(self):
        self._database = None

    @property
    def db(self):
        if self._database is None:
            if options.CFG.uri and 'replicaSet' in options.CFG.uri:
                conn = pymongo.MongoReplicaSetClient(options.CFG.uri)
            else:
                conn = pymongo.MongoClient(options.CFG.uri)

            self._database = conn[options.CFG.database]

        return self._database

    @property
    def partitions_controller(self):
        return controllers.PartitionsController(self)

    @property
    def catalogue_controller(self):
        return controllers.CatalogueController(self)

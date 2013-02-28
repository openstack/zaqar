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

"""
Mongodb storage driver implementation
"""

import pymongo
import pymongo.errors

from marconi.common import config
from marconi import storage
from marconi.storage.mongodb import controllers

options = {
    "uri": None,
    "database": "marconi",
}

cfg = config.namespace('drivers:storage:mongodb').from_options(**options)


class Driver(storage.DriverBase):

    def __init__(self):
        self._database = None

    @property
    def db(self):
        """
        Property for lazy instantiation of
        mongodb's database.
        """
        if not self._database:
            conn = pymongo.MongoClient(cfg.uri)
            self._database = conn[cfg.database]

        return self._database

    @property
    def queue_controller(self):
        return controllers.QueueController(self)

    @property
    def message_controller(self):
        return controllers.MessageController(self)

    @property
    def claim_controller(self):
        return controllers.ClaimController(self)

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
from marconi.proxy.storage import base
from marconi.proxy.storage.memory import controllers


class Driver(base.DriverBase):

    def __init__(self):
        self._db = {}

    @property
    def db(self):
        return self._db

    @property
    def partitions_controller(self):
        return controllers.PartitionsController(self)

    @property
    def catalogue_controller(self):
        return controllers.CatalogueController(self)

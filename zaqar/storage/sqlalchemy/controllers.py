# Copyright (c) 2014 Red Hat, Inc.
# Copyright (c) 2014 Rackspace Hosting Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

from zaqar.storage.sqlalchemy import catalogue
from zaqar.storage.sqlalchemy import flavors
from zaqar.storage.sqlalchemy import pools
from zaqar.storage.sqlalchemy import queues


QueueController = queues.QueueController
CatalogueController = catalogue.CatalogueController
PoolsController = pools.PoolsController
FlavorsController = flavors.FlavorsController

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

"""Exports Mongodb storage controllers.

Field Mappings:
    In order to reduce the disk / memory space used,
    fields name will be, most of the time, the first
    letter of their long name. Fields mapping will be
    updated and documented in each controller class.
"""

from zaqar.storage.mongodb import catalogue
from zaqar.storage.mongodb import claims
from zaqar.storage.mongodb import flavors
from zaqar.storage.mongodb import messages
from zaqar.storage.mongodb import pools
from zaqar.storage.mongodb import queues
from zaqar.storage.mongodb import subscriptions


CatalogueController = catalogue.CatalogueController
ClaimController = claims.ClaimController
FlavorsController = flavors.FlavorsController
MessageController = messages.MessageController
FIFOMessageController = messages.FIFOMessageController
QueueController = queues.QueueController
PoolsController = pools.PoolsController
SubscriptionController = subscriptions.SubscriptionController

# Copyright (c) 2013 Rackspace, Inc.
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

import abc


class DriverBase(object):
    """Base class for Transport Drivers to document the expected interface.

    :param storage: The storage driver
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, storage):
        self.storage = storage

    @abc.abstractmethod
    def listen():
        """Start listening for client requests (self-hosting mode)."""
        raise NotImplementedError

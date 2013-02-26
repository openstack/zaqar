# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import marconi.storage as storage


class Driver(storage.DriverBase):

    def __init__(self, cfg):
        self._cfg = cfg

    @property
    def queue_controller(self):
        # TODO(kgriffs): Create base classes for controllers in common/
        return None

    @property
    def message_controller(self):
        # TODO(kgriffs): Create base classes for controllers in common/
        return None

    @property
    def claim_controller(self):
        # TODO(kgriffs): Create base classes for controllers in common/
        return None

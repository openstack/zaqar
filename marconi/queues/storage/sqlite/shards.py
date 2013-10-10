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
#
# See the License for the specific language governing permissions and
# limitations under the License.

from marconi.queues.storage import base


class ShardsController(base.ShardsBase):

    def list(self, marker=None, limit=10, detailed=False):
        pass

    def get(self, name, detailed=False):
        pass

    def create(self, name, weight, uri, options=None):
        pass

    def exists(self, name):
        pass

    def update(self, name, **kwargs):
        pass

    def delete(self, name):
        pass

    def drop_all(self):
        pass

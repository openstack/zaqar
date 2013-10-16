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

"""sqlite storage controller for the queues catalogue.

Serves to construct an association between a project + queue -> shard
"""

from marconi.queues.storage import base


class CatalogueController(base.CatalogueBase):

    def __init__(self, *args, **kwargs):
        super(CatalogueController, self).__init__(*args, **kwargs)

    def list(self, project):
        pass

    def get(self, project, queue):
        pass

    def exists(self, project, queue):
        pass

    def insert(self, project, queue, shard):
        pass

    def delete(self, project, queue):
        pass

    def update(self, project, queue, shards=None):
        pass

    def drop_all(self):
        pass

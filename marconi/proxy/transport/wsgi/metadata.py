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
"""metadata: adds queue metadata to the catalogue and forwards to
marconi queue metadata requests.
"""
import io
import json

from marconi.proxy.utils import forward
from marconi.proxy.utils import helpers


class Resource(forward.ForwardMixin):
    def __init__(self, partitions_controller,
                 catalogue_controller,
                 cache, selector):
        super(Resource, self).__init__(
            partitions_controller, catalogue_controller,
            cache, selector, methods=['get'])

    def on_put(self, request, response, queue):
        project = helpers.get_project(request)
        data = request.stream.read()

        # NOTE(cpp-cabrera): This is a hack to preserve the metadata
        request.stream = io.BytesIO(data)
        resp = self.forward(request, response, queue)

        if resp.ok:
            self._catalogue.update_metadata(project, queue,
                                            json.loads(data))

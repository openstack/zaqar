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

import falcon

from marconi.proxy.storage import exceptions
from marconi.proxy.utils import helpers
from marconi.proxy.utils import http


class Resource(object):
    def __init__(self, partitions_controller, catalogue_controller):
        self._partitions = partitions_controller
        self._catalogue = catalogue_controller

    def _forward(self, request, response, queue):
        project = helpers.get_project(request)

        partition = None
        try:
            partition = self._catalogue.get(project, queue)['partition']
        except exceptions.EntryNotFound:
            raise falcon.HTTPNotFound()

        host = self._partitions.select(partition)
        resp = helpers.forward(host, request)
        response.status = http.status(resp.status_code)
        response.body = resp.content

        return resp

    def on_get(self, request, response, queue):
        self._forward(request, response, queue)

    def on_put(self, request, response, queue):
        project = helpers.get_project(request)
        data = request.stream.read()

        # NOTE(cpp-cabrera): This is a hack to preserve the metadata
        request.stream = io.BytesIO(data)
        resp = self._forward(request, response, queue)

        if resp.ok:
            self._catalogue.update_metadata(project, queue,
                                            json.loads(data))

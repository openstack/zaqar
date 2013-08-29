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
import falcon
import msgpack
import requests

from marconi.proxy.utils import helpers
from marconi.proxy.utils import http


class Resource(object):
    def __init__(self, client):
        self.client = client

    def _make_key(self, request, queue):
        project = helpers.get_project(request)
        return 'q.%s.%s' % (project, queue)

    def on_get(self, request, response, queue):
        resp = helpers.forward(self.client, request, queue)
        response.status = http.status(resp.status_code)
        response.body = resp.content

    def on_put(self, request, response, queue):
        key = self._make_key(request, queue)
        if not self.client.exists(key):
            raise falcon.HTTPNotFound()

        resp = helpers.forward(self.client, request, queue)
        response.status = http.status(resp.status_code)
        response.body = resp.content

        if resp.ok:
            project = helpers.get_project(request)
            host = helpers.get_host_by_project_and_queue(self.client,
                                                         project, queue)
            resp = requests.get(host + '/v1/queues/%s/metadata' % queue)
            self.client.hset(key, 'm', msgpack.dumps(resp.json()))

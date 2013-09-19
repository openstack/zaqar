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
"""catalogue: maintains a directory of all queues proxied through the system.
"""
import json

import falcon

from marconi.proxy.storage import exceptions
from marconi.proxy.utils import helpers


class Listing(object):
    """A listing of all entries in the catalogue."""
    def __init__(self, catalogue_controller):
        self._catalogue = catalogue_controller

    def on_get(self, request, response):
        project = helpers.get_project(request)

        resp = {}
        for q in self._catalogue.list(project):
            resp[q['name']] = q

        if not resp:
            response.status = falcon.HTTP_204
            return

        response.status = falcon.HTTP_200
        response.body = json.dumps(resp, ensure_ascii=False)


class Resource(object):
    """A single catalogue entry."""
    def __init__(self, catalogue_controller):
        self._catalogue = catalogue_controller

    def on_get(self, request, response, queue):
        project = helpers.get_project(request)
        entry = None
        try:
            entry = self._catalogue.get(project, queue)
        except exceptions.EntryNotFound:
            raise falcon.HTTPNotFound()

        resp = entry
        response.status = falcon.HTTP_200
        response.body = json.dumps(resp, ensure_ascii=False)

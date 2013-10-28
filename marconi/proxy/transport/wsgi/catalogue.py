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

from marconi.openstack.common import log
from marconi.proxy.storage import errors
from marconi.proxy.utils import helpers


LOG = log.getLogger(__name__)


class Listing(object):
    """A listing of all entries in the catalogue

    :param catalogue_controller: handles storage details
    """
    def __init__(self, catalogue_controller):
        self._catalogue = catalogue_controller

    def on_get(self, request, response):
        project = helpers.get_project(request)
        LOG.debug('LIST catalogue - project: {0}'.format(project))

        resp = list(self._catalogue.list(project))

        if not resp:
            response.status = falcon.HTTP_204
            return

        response.status = falcon.HTTP_200
        response.body = json.dumps(resp, ensure_ascii=False)


class Resource(object):
    """A single catalogue entry

    :param catalogue_controller: handles storage details
    """
    def __init__(self, catalogue_controller):
        self._catalogue = catalogue_controller

    def on_get(self, request, response, queue):
        project = helpers.get_project(request)
        LOG.debug('GET catalogue - project/queue: {0}/{1}'.format(
            project, queue
        ))
        entry = None
        try:
            entry = self._catalogue.get(project, queue)
        except errors.EntryNotFound:
            LOG.debug('Entry not found')
            raise falcon.HTTPNotFound()

        response.status = falcon.HTTP_200
        response.body = json.dumps(entry, ensure_ascii=False)

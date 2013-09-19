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
"""v1: queries the first node in the first partition for a homedoc."""
import falcon

from marconi.proxy.utils import helpers
from marconi.proxy.utils import http


class Resource(object):
    """Forwards homedoc requests to marconi queues API

    :param partitions_controller: controller for handling partitions
    """
    def __init__(self, partitions_controller):
        self._partitions = partitions_controller

    def on_get(self, request, response):
        partition = None
        try:
            partition = next(self._partitions.list())
        except StopIteration:
            raise falcon.HTTPServiceUnavailable(
                "No partitions found",
                "Register some partitions",
                retry_after=120
            )

        host = partition['hosts'][0]
        resp = helpers.forward(host, request)

        response.set_headers(helpers.capitalized(resp.headers))
        response.status = http.status(resp.status_code)
        response.body = resp.content

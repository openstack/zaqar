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
"""health: queries the first node in the first partition for health
responses.
"""
import requests

from marconi.proxy.utils import helpers
from marconi.proxy.utils import http


class Resource(object):
    def __init__(self, client):
        self.client = client

    def on_get(self, request, response):
        node = helpers.get_first_host(self.client)
        resp = requests.get(node + '/v1/health')
        response.status = http.status(resp.status_code)
        response.body = resp.content

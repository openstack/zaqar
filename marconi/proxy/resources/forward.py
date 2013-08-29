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
"""forward: a resource for each marconi route where the desired result
is to just pass along a request to marconi.
"""
from marconi.proxy.utils import helpers
from marconi.proxy.utils import http


# TODO(cpp-cabrera): Replace these with falcon.set_default_route
#                    once that lands for DRYer forwarding


class ClaimCreate(object):
    """Handler for the endpoint to post claims."""
    def __init__(self, client):
        self.client = client

    def on_post(self, request, response, queue):
        resp = helpers.forward(self.client, request, queue)
        response.set_headers(resp.headers)
        response.status = http.status(resp.status_code)
        response.body = resp.content


class Claim(object):
    """Handler for dealing with claims directly."""
    def __init__(self, client):
        self.client = client

    def _forward_claim(self, request, response, queue):
        resp = helpers.forward(self.client, request, queue)
        response.set_headers(resp.headers)
        response.status = http.status(resp.status_code)
        response.body = resp.content

    def on_patch(self, request, response, queue, cid):
        self._forward_claim(request, response, queue)

    def on_delete(self, request, response, queue, cid):
        self._forward_claim(request, response, queue)

    def on_get(self, request, response, queue, cid):
        self._forward_claim(request, response, queue)


class MessageBulk(object):
    """Handler for bulk message operations."""
    def __init__(self, client):
        self.client = client

    def _forward_message(self, request, response, queue):
        resp = helpers.forward(self.client, request, queue)
        response.set_headers(resp.headers)
        response.status = http.status(resp.status_code)
        response.body = resp.content

    def on_get(self, request, response, queue):
        self._forward_message(request, response, queue)

    def on_delete(self, request, response, queue):
        self._forward_message(request, response, queue)

    def on_post(self, request, response, queue):
        self._forward_message(request, response, queue)


class Message(object):
    """Handler for individual messages."""
    def __init__(self, client):
        self.client = client

    def _forward_message(self, request, response, queue):
        resp = helpers.forward(self.client, request, queue)
        response.set_headers(resp.headers)
        response.status = http.status(resp.status_code)
        response.body = resp.content

    def on_get(self, request, response, queue, mid):
        self._forward_message(request, response, queue)

    def on_delete(self, request, response, queue, mid):
        self._forward_message(request, response, queue)


class Stats(object):
    """Handler for forwarding queue stats requests."""
    def __init__(self, client):
        self.client = client

    def _forward_stats(self, request, response, queue):
        resp = helpers.forward(self.client, request, queue)
        response.set_headers(resp.headers)
        response.status = http.status(resp.status_code)
        response.body = resp.content

    def on_get(self, request, response, queue):
        self._forward_stats(request, response, queue)

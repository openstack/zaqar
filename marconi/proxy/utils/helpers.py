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
"""helpers: utilities for performing common operations for resources."""
import falcon
import msgpack
import requests


def get_first_host(client):
    """Returns the first host from the first partition."""
    try:
        partition = next(p.decode('utf8') for p in
                         client.lrange('ps', 0, 0))
    except StopIteration:
        raise falcon.HTTPNotFound('No partitions registered')
    key = 'p.%s' % partition
    ns = msgpack.loads(client.hget(key, 'n'))
    return next(n.decode('utf8') for n in ns)


def get_host_by_project_and_queue(client, project, queue):
    """Fetches the host address for a given project and queue.

    :returns: a host address as stored or None if not found
    """
    key = 'q.%s.%s' % (project, queue)
    if not client.exists(key):
        return None
    return client.hget(key, 'h').decode('utf8')


def get_project(request):
    """Retrieves the Project-Id header from a request.

    :returns: The Project-Id value or '_' if not provided
    """
    return request.get_header('x_project_id') or '_'


def forward(client, request, queue):
    """Forwards a request to the appropriate host based on the location
    of a given queue.

    :returns: a python-requests response object
    :raises: falcon.HTTPNotFound if the queue cannot be found in the catalogue
    """
    project = get_project(request)
    host = get_host_by_project_and_queue(client, project, queue)
    if not host:
        raise falcon.HTTPNotFound()
    url = host + request.path
    if request.query_string:
        url += '?' + request.query_string
    method = request.method.lower()
    resp = requests.request(method, url, headers=request._headers,
                            data=request.stream.read())
    return resp

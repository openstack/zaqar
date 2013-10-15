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

import requests


def get_project(request):
    """Retrieves the Project-Id header from a request.

    :param request: falcon.Request
    :returns: The Project-Id value or '_' if not provided
    """
    return request.get_header('x_project_id') or '_'


# TODO(cpp-cabrera): when falcon 0.1.7 lands in openstack
# requirements, move to use the request.headers property instead of
# this function.
def canonicalize(headers):
    """Converts headers from WSGI:Content_Length -> HTTP:C-A

    :param headers: A dictionary of {'name': 'value'} header items
    :type headers: dict
    :returns: HTTP-canonicalized headers
    :rtype: dict
    """
    return dict([(k.replace('_', '-'), v) for k, v in headers.items()])


def forward(host, request):
    """Forwards a request.

    :param host: str - URL to host to use
    :param request: falcon.Request
    :returns: a python-requests response object
    """
    url = host + request.path
    if request.query_string:
        url += '?' + request.query_string
    method = request.method.lower()
    resp = requests.request(method, url,
                            headers=canonicalize(request._headers),
                            data=request.stream)
    return resp


def capitalized(headers):
    """Construct a new headers dict with all keys capitalized.

    :returns: a new dict of headers in This-Form
    """
    d = {}
    for k, v in headers.items():
        nk = '-'.join([w.capitalize() for w in k.split('-')])
        d[nk] = v

    return d

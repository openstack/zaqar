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

    :returns: The Project-Id value or '_' if not provided
    """
    return request.get_header('x_project_id') or '_'


def forward(host, request):
    """Forwards a request.

    :returns: a python-requests response object
    """
    url = host + request.path
    if request.query_string:
        url += '?' + request.query_string
    method = request.method.lower()
    resp = requests.request(method, url, headers=request._headers,
                            data=request.stream.read())
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

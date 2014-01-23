# Copyright (c) 2013 Rackspace, Inc.
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

import functools
import json

import requests


def _build_url(method):

    @functools.wraps(method)
    def wrapper(self, url='', **kwargs):

        if not url.startswith("http"):
            if not self.base_url:
                raise RuntimeError("Base url not set")

            url = self.base_url + url or ''

        return method(self, url, **kwargs)

    return wrapper


class Client(object):

    def __init__(self):
        self.base_url = None
        self.session = requests.session()

    def set_base_url(self, base_url):
        self.base_url = base_url

    def set_headers(self, headers):
        self.session.headers.update(headers)

    @_build_url
    def get(self, url=None, **kwargs):
        """Does  http GET."""
        return self.session.get(url, **kwargs)

    @_build_url
    def head(self, url=None, **kwargs):
        """Does  http HEAD."""
        return self.session.head(url, **kwargs)

    @_build_url
    def post(self, url=None, **kwargs):
        """Does  http POST."""

        if "data" in kwargs:
            kwargs['data'] = json.dumps(kwargs["data"])

        return self.session.post(url, **kwargs)

    @_build_url
    def put(self, url=None, **kwargs):
        """Does  http PUT."""

        if "data" in kwargs:
            kwargs['data'] = json.dumps(kwargs["data"])

        return self.session.put(url, **kwargs)

    @_build_url
    def delete(self, url=None, **kwargs):
        """Does  http DELETE."""
        return self.session.delete(url, **kwargs)

    @_build_url
    def patch(self, url=None, **kwargs):
        """Does  http PATCH."""
        if "data" in kwargs:
            kwargs['data'] = json.dumps(kwargs["data"])
        return self.session.patch(url, **kwargs)

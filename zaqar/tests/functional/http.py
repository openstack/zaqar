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

from falcon import testing as ftest
from oslo_serialization import jsonutils
import requests
import six


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
        # NOTE(kgriffs): used by @_build_url
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


class ResponseMock(object):
    """Mocks part of the Requests library's Response object."""

    def __init__(self, srmock, wsgi_result):
        self.status_code = int(srmock.status.partition(' ')[0])
        self._body = wsgi_result[0] if wsgi_result else ''
        self.headers = srmock.headers_dict

    def json(self):
        return jsonutils.loads(self._body)


class WSGIClient(object):
    """Same interface as Client, but speaks directly to a WSGI callable."""

    def __init__(self, app):
        # NOTE(kgriffs): used by @_build_url
        self.base_url = None

        self.app = app
        self.headers = {}

    @staticmethod
    def _sanitize_headers(headers):
        # NOTE(kgriffs): Workaround for a little create_environ bug
        return dict([(key, '' if value is None else value)
                     for key, value in headers.items()])

    def _simulate_request(self, url, method='GET', data=None,
                          headers=None, params=None):
        """Simulate a request.

        Simulates a WSGI request to the API for testing.

        :param url: Request path for the desired resource
        :param method: (Default 'GET') The HTTP method to send
        :param data: (Default None) A dict that will be serialized
            to JSON and submitted as the body of the request. May
            also be a pre-serialized string.
        :param headers: (Default None) A dict containing
            extra HTTP headers to send.
        :param params: (Default None) A dict of parameters
            to use in the query string for the request.

        :returns: a requests response instance
        """

        if headers is None:
            headers = self.headers

        headers = self._sanitize_headers(headers)

        if data is None:
            body = ''
        elif isinstance(data, str) or isinstance(data, six.text_type):
            body = data
        else:
            body = json.dumps(data, ensure_ascii=False)

        parsed_url = six.moves.urllib_parse.urlparse(url)

        query = parsed_url.query

        if params is not None:
            extra = '&'.join([key + '=' + str(value)
                             for key, value in params.items()])

            query += '&' + extra

        environ = ftest.create_environ(method=method,
                                       path=parsed_url.path,
                                       query_string=query,
                                       headers=headers,
                                       body=body)

        srmock = ftest.StartResponseMock()
        wsgi_result = self.app(environ, srmock)

        return ResponseMock(srmock, wsgi_result)

    def set_base_url(self, base_url):
        self.base_url = base_url

    def set_headers(self, headers):
        self.headers.update(headers)

    @_build_url
    def get(self, url=None, **kwargs):
        """Simulate a GET request."""
        kwargs['method'] = 'GET'
        return self._simulate_request(url=url, **kwargs)

    @_build_url
    def head(self, url=None, **kwargs):
        """Simulate a HEAD request."""
        kwargs['method'] = 'HEAD'
        return self._simulate_request(url=url, **kwargs)

    @_build_url
    def post(self, url=None, **kwargs):
        """Simulate a POST request."""
        kwargs['method'] = 'POST'
        return self._simulate_request(url=url, **kwargs)

    @_build_url
    def put(self, url=None, **kwargs):
        """Simulate a PUT request."""
        kwargs['method'] = 'PUT'
        return self._simulate_request(url=url, **kwargs)

    @_build_url
    def delete(self, url=None, **kwargs):
        """Simulate a DELETE request."""
        kwargs['method'] = 'DELETE'
        return self._simulate_request(url=url, **kwargs)

    @_build_url
    def patch(self, url=None, **kwargs):
        """Simulate a PATCH request."""
        kwargs['method'] = 'PATCH'
        return self._simulate_request(url=url, **kwargs)

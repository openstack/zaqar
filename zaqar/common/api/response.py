# Copyright (c) 2013 Red Hat, Inc.
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


class Response(object):
    """Common response class for Zaqar.

    All `zaqar.transport.base.Transport` implementations
    will return this to the higher level API which will then build
    an object out of it.

    :param request: The request sent to the server.
    :type request: `zaqar.transport.request.Request`
    :param body: Response's body
    :type body: `six.string_types`
    :param headers: Optional headers returned in the response.
    :type headers: dict
    """

    __slots__ = ('_request', '_body', '_headers')

    def __init__(self, request, body, headers=None):
        self._request = request
        self._body = body
        self._headers = headers or {}

    def get_response(self):
        return {'request': self._request.get_request(),
                'body': self._body,
                'headers': self._headers}

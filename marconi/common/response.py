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
    """Common response class for Marconi.

    All `marconi.transport.base.Transport` implementations
    will return this to the higher level API which will then build
    an object out of it.

    :param request: The request sent to the server.
    :type: `marconi.transport.request.Request`
    :param content: Response's content
    :type: `six.string_types`
    :param headers: Optional headers returned in the response.
    :type: dict
    """

    __slots__ = ('request', 'content', 'headers')

    def __init__(self, request, content, headers=None):
        self.request = request
        self.content = content
        self.headers = headers or {}

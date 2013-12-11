# Copyright (c) 2013 Rackspace, Inc.
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

import json

from marconi.common import decorators


class Request(object):
    """General data for a Marconi request

    Transport will generate a request object and send to this the API to be
    processed.
    :param operation: Operation to identify the API call being processed, i.e:
        - get_queues
        - get_messages
    :type operation: str
    :param content: Request's body. Default: None
    :type content: str
    :param params: Query string params. Default: None
    :type params: dict
    :param headers: Request headers. Default: None
    :type headers: dict
    :param api: Api entry point. i.e: 'queues.v1'
    :type api: `six.text_type`.
    """

    def __init__(self, operation='',
                 content=None, params=None,
                 headers=None, api=None):

        self._api = None
        self._api_mod = api

        self.operation = operation
        self.content = content
        self.params = params or {}
        self.headers = headers or {}

    @decorators.lazy_property()
    def deserialized_content(self):
        if self.content is not None:
            return json.loads(self.content)
        return None

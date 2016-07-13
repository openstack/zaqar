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


class Request(object):
    """General data for a Zaqar request

    Transport will generate a request object and send to this the API to be
    processed.
    :param action: Action to identify the API call being processed,
    i.e: 'get_queues', 'get_messages'
    :type action: str
    :param body: Request's body. Default: None
    :type body: str
    :param headers: Request headers. Default: None
    :type headers: dict
    :param api: Api entry point. i.e: 'queues.v1'
    :type api: `six.text_type`.
    :param env: Request environment. Default: None
    :type env: dict
    """

    def __init__(self, action,
                 body=None, headers=None, api=None, env=None):
        self._action = action
        self._body = body
        self._headers = headers or {}
        self._api = api
        self._env = env or {}

    def get_request(self):
        return {'action': self._action,
                'body': self._body,
                'headers': self._headers,
                'api': self._api}

# Copyright (c) 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

from zaqar.api.v1_1 import endpoints


class Handler(object):
    """Defines API handler

    The handler validates and process the requests
    """

    def __init__(self, storage, control, validate, defaults):
        self.v1_1_endpoints = endpoints.Endpoints(storage, control,
                                                  validate, defaults)

    def process_request(self, req):
        # FIXME(vkmc): Control API version
        return getattr(self.v1_1_endpoints, req._action)(req)
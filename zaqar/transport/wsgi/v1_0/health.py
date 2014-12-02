# Copyright (c) 2013 Rackspace, Inc.
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

import falcon


class Resource(object):

    __slots__ = ('_driver',)

    def __init__(self, driver):
        self._driver = driver

    def on_get(self, req, resp, **kwargs):
        resp.status = (falcon.HTTP_204 if self._driver.is_alive()
                       else falcon.HTTP_503)

    def on_head(self, req, resp, **kwargs):
        resp.status = falcon.HTTP_204

# Copyright (c) 2014 OpenStack Foundation
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

from zaqar.transport import utils
from zaqar.transport.wsgi import v1_0
from zaqar.transport.wsgi import v1_1
from zaqar.transport.wsgi import v2_0

VERSIONS = {
    'versions': [
        v1_0.VERSION,
        v1_1.VERSION,
        v2_0.VERSION
    ]
}


class Resource(object):

    def __init__(self):
        self.versions = utils.to_json(VERSIONS)

    def on_get(self, req, resp, project_id):
        resp.body = self.versions

        resp.status = falcon.HTTP_300

# Copyright 2017 OpenStack, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_log import log
from oslo_middleware import cors

LOG = log.getLogger(__name__)


class CORSMiddleware(object):

    @classmethod
    def install(cls, app, conf):

        LOG.debug(u'Installing CORS middleware.')
        cors.set_defaults(
            allow_headers=['X-Auth-Token',
                           'X-Identity-Status',
                           'X-Roles',
                           'X-Service-Catalog',
                           'X-User-Id',
                           'X-Tenant-Id',
                           'X-OpenStack-Request-ID',
                           'X-Trace-Info',
                           'X-Trace-HMAC',
                           'Client-id'],
            expose_headers=['X-Auth-Token',
                            'X-Subject-Token',
                            'X-Service-Token',
                            'X-OpenStack-Request-ID'],
            allow_methods=['GET',
                           'PUT',
                           'POST',
                           'DELETE',
                           'PATCH',
                           'HEAD']
        )

        return cors.CORS(app, conf)


def install_cors(app, conf):
    return CORSMiddleware.install(app, conf)

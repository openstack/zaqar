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

import functools

import zaqar.common.api.response as response
from zaqar.i18n import _
import zaqar.openstack.common.log as logging
from zaqar.transport import utils

LOG = logging.getLogger(__name__)


def raises_conn_error(func):
    """Handles generic Exceptions

    This decorator catches generic Exceptions and returns a generic
    Response.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            LOG.exception(ex)
            error = _("Unexpected error.")
            req = kwargs.get('req')
            return error_response(req, ex, error)

    return wrapper


def error_response(req, exception, headers=None, error=None):
    body = utils.to_json({'exception': exception,
                          'error': error})
    resp = response.Response(req, body, headers)
    return resp
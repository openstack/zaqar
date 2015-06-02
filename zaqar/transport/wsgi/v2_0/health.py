# Copyright (c) 2014 Rackspace, Inc.
# Copyright 2014 Catalyst IT Ltd.
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

from oslo_log import log as logging

from zaqar.i18n import _
from zaqar.transport import utils
from zaqar.transport.wsgi import errors as wsgi_errors

LOG = logging.getLogger(__name__)


class Resource(object):

    __slots__ = ('_driver',)

    def __init__(self, driver):
        self._driver = driver

    def on_get(self, req, resp, **kwargs):
        try:
            resp_dict = self._driver.health()
            resp.body = utils.to_json(resp_dict)
        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Health status could not be read.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

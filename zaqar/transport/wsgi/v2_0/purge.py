# Copyright 2016 Catalyst IT Ltd.
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

from oslo_log import log as logging
import six

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar.transport import acl
from zaqar.transport import validation
from zaqar.transport.wsgi import errors as wsgi_errors
from zaqar.transport.wsgi import utils as wsgi_utils

LOG = logging.getLogger(__name__)


class Resource(object):

    __slots__ = ('_driver', '_conf', '_queue_ctrl',
                 '_message_ctrl', '_subscription_ctrl', '_validate')

    def __init__(self, driver):
        self._driver = driver
        self._conf = driver._conf
        self._queue_ctrl = driver._storage.queue_controller
        self._message_ctrl = driver._storage.message_controller
        self._subscription_ctrl = driver._storage.subscription_controller
        self._validate = driver._validate

    @decorators.TransportLog("Queues item")
    @acl.enforce("queues:purge")
    def on_post(self, req, resp, project_id, queue_name):
        try:
            if req.content_length:
                document = wsgi_utils.deserialize(req.stream,
                                                  req.content_length)
                self._validate.queue_purging(document)
            else:
                document = {'resource_types': ['messages', 'subscriptions']}
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        try:
            if "messages" in document['resource_types']:
                pop_limit = 100
                LOG.debug("Purge all messages under queue %s", queue_name)
                messages = self._message_ctrl.pop(queue_name, pop_limit,
                                                  project=project_id)
                while messages:
                    messages = self._message_ctrl.pop(queue_name, pop_limit,
                                                      project=project_id)

            if "subscriptions" in document['resource_types']:
                LOG.debug("Purge all subscriptions under queue %s", queue_name)
                results = self._subscription_ctrl.list(queue_name,
                                                       project=project_id)
                subscriptions = list(next(results))
                for sub in subscriptions:
                    self._subscription_ctrl.delete(queue_name,
                                                   sub['id'],
                                                   project=project_id)
        except ValueError as err:
            raise wsgi_errors.HTTPBadRequestAPI(str(err))
        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Queue could not be purged.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204

# Copyright 2019 Catalyst IT Ltd.
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

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar.transport import acl
from zaqar.transport import validation
from zaqar.transport.wsgi import errors as wsgi_errors
from zaqar.transport.wsgi import utils as wsgi_utils

LOG = logging.getLogger(__name__)


class Resource(object):

    __slots__ = ('_driver', '_conf',
                 '_message_ctrl', '_subscription_ctrl', '_validate')

    def __init__(self, driver):
        self._driver = driver
        self._conf = driver._conf
        self._message_ctrl = driver._storage.message_controller
        self._subscription_ctrl = driver._storage.subscription_controller
        self._validate = driver._validate

    @decorators.TransportLog("Topics item")
    @acl.enforce("topics:purge")
    def on_post(self, req, resp, project_id, topic_name):
        try:
            if req.content_length:
                document = wsgi_utils.deserialize(req.stream,
                                                  req.content_length)
                self._validate.queue_purging(document)
            else:
                document = {'resource_types': ['messages', 'subscriptions']}
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(str(ex))

        try:
            if "messages" in document['resource_types']:
                pop_limit = 100
                LOG.debug("Purge all messages under topic %s", topic_name)
                messages = self._message_ctrl.pop(topic_name, pop_limit,
                                                  project=project_id)
                while messages:
                    messages = self._message_ctrl.pop(topic_name, pop_limit,
                                                      project=project_id)

            if "subscriptions" in document['resource_types']:
                LOG.debug("Purge all subscriptions under topic %s", topic_name)
                results = self._subscription_ctrl.list(topic_name,
                                                       project=project_id)
                subscriptions = list(next(results))
                for sub in subscriptions:
                    self._subscription_ctrl.delete(topic_name,
                                                   sub['id'],
                                                   project=project_id)
        except ValueError as err:
            raise wsgi_errors.HTTPBadRequestAPI(str(err))
        except Exception:
            description = _(u'Topic could not be purged.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204

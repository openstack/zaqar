# Copyright (c) 2013 Rackspace, Inc.
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

import falcon
from oslo_log import log as logging
import six

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar.storage import errors as storage_errors
from zaqar.transport import utils
from zaqar.transport import validation
from zaqar.transport.wsgi import errors as wsgi_errors
from zaqar.transport.wsgi import utils as wsgi_utils


LOG = logging.getLogger(__name__)


class Resource(object):
    __slots__ = ('_wsgi_conf', '_validate', '_queue_ctrl')

    def __init__(self, _wsgi_conf, validate, queue_controller):
        self._wsgi_conf = _wsgi_conf
        self._validate = validate
        self._queue_ctrl = queue_controller

    @decorators.TransportLog("Queue metadata")
    def on_get(self, req, resp, project_id, queue_name):
        try:
            resp_dict = self._queue_ctrl.get_metadata(queue_name,
                                                      project=project_id)

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Queue metadata could not be retrieved.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.content_location = req.path
        resp.body = utils.to_json(resp_dict)
        # status defaults to 200

    @decorators.TransportLog("Queue metadata")
    def on_put(self, req, resp, project_id, queue_name):
        try:
            # Place JSON size restriction before parsing
            self._validate.queue_metadata_length(req.content_length)
            # Deserialize queue metadata
            document = wsgi_utils.deserialize(req.stream, req.content_length)
            metadata = wsgi_utils.sanitize(document)
            # Restrict setting any reserved queue attributes
            for key in metadata:
                if key.startswith('_'):
                    description = _(u'Reserved queue attributes in metadata '
                                    u'(which names start with "_") can not be '
                                    u'set in API v1.')
                    raise validation.ValidationFailed(description)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        try:
            self._queue_ctrl.set_metadata(queue_name,
                                          metadata=metadata,
                                          project=project_id)

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except storage_errors.QueueDoesNotExist as ex:
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Metadata could not be updated.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204
        resp.location = req.path

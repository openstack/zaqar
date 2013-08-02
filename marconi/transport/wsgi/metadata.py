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

from marconi.common import config
import marconi.openstack.common.log as logging
from marconi.storage import exceptions as storage_exceptions
from marconi.transport import helpers
from marconi.transport.wsgi import exceptions as wsgi_exceptions


LOG = logging.getLogger(__name__)
CFG = config.namespace('drivers:transport:wsgi').from_options(
    metadata_max_length=64 * 1024
)


class Resource(object):
    __slots__ = ('queue_ctrl', )

    def __init__(self, queue_controller):
        self.queue_ctrl = queue_controller

    def on_get(self, req, resp, project_id, queue_name):
        LOG.debug(_("Queue metadata GET - queue: %(queue)s, "
                    "project: %(project)s") %
                  {"queue": queue_name, "project": project_id})

        try:
            resp_dict = self.queue_ctrl.get_metadata(queue_name,
                                                     project=project_id)

        except storage_exceptions.DoesNotExist:
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _('Queue metadata could not be retrieved.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        resp.content_location = req.path
        resp.body = helpers.to_json(resp_dict)
        resp.status = falcon.HTTP_200

    def on_put(self, req, resp, project_id, queue_name):
        LOG.debug(_("Queue metadata PUT - queue: %(queue)s, "
                    "project: %(project)s") %
                  {"queue": queue_name, "project": project_id})

        # Place JSON size restriction before parsing
        if req.content_length > CFG.metadata_max_length:
            description = _('Queue metadata size is too large.')
            raise wsgi_exceptions.HTTPBadRequestBody(description)

        # Deserialize queue metadata
        try:
            metadata = helpers.read_json(req.stream, req.content_length)
        except helpers.MalformedJSON:
            description = _('Request body could not be parsed.')
            raise wsgi_exceptions.HTTPBadRequestBody(description)
        except Exception as ex:
            LOG.exception(ex)
            description = _('Request body could not be read.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        # Metadata must be a JSON object
        if not isinstance(metadata, dict):
            description = _('Queue metadata must be an object.')
            raise wsgi_exceptions.HTTPBadRequestBody(description)

        try:
            self.queue_ctrl.set_metadata(queue_name,
                                         metadata=metadata,
                                         project=project_id)

        except storage_exceptions.QueueDoesNotExist:
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _('Metadata could not be updated.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204
        resp.location = req.path

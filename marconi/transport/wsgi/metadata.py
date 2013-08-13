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
from marconi.common import exceptions as input_exceptions
import marconi.openstack.common.log as logging
from marconi.storage import exceptions as storage_exceptions
from marconi.transport import utils
from marconi.transport import validation as validate
from marconi.transport.wsgi import exceptions as wsgi_exceptions
from marconi.transport.wsgi import utils as wsgi_utils


LOG = logging.getLogger(__name__)
CFG = config.namespace('drivers:transport:wsgi').from_options(
    metadata_max_length=64 * 1024
)


class Resource(object):
    __slots__ = ('queue_ctrl', )

    def __init__(self, queue_controller):
        self.queue_ctrl = queue_controller

    def on_get(self, req, resp, project_id, queue_name):
        LOG.debug(_(u'Queue metadata GET - queue: %(queue)s, '
                    u'project: %(project)s') %
                  {'queue': queue_name, 'project': project_id})

        try:
            resp_dict = self.queue_ctrl.get_metadata(queue_name,
                                                     project=project_id)

        except storage_exceptions.DoesNotExist:
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Queue metadata could not be retrieved.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        resp.content_location = req.path
        resp.body = utils.to_json(resp_dict)
        resp.status = falcon.HTTP_200

    def on_put(self, req, resp, project_id, queue_name):
        LOG.debug(_(u'Queue metadata PUT - queue: %(queue)s, '
                    u'project: %(project)s') %
                  {'queue': queue_name, 'project': project_id})

        # Place JSON size restriction before parsing
        if req.content_length > CFG.metadata_max_length:
            description = _(u'Queue metadata size is too large.')
            raise wsgi_exceptions.HTTPBadRequestBody(description)

        # Deserialize queue metadata
        metadata, = wsgi_utils.filter_stream(req.stream,
                                             req.content_length,
                                             spec=None)

        try:
            validate.queue_content(
                metadata, check_size=(
                    validate.CFG.metadata_size_uplimit <
                    CFG.metadata_max_length))
            self.queue_ctrl.set_metadata(queue_name,
                                         metadata=metadata,
                                         project=project_id)

        except input_exceptions.ValidationFailed as ex:
            raise wsgi_exceptions.HTTPBadRequestBody(str(ex))

        except storage_exceptions.QueueDoesNotExist:
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Metadata could not be updated.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204
        resp.location = req.path

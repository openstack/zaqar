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
import six

import marconi.openstack.common.log as logging
from marconi.queues.storage import errors as storage_errors
from marconi.queues.transport import utils
from marconi.queues.transport import validation
from marconi.queues.transport.wsgi import errors as wsgi_errors
from marconi.queues.transport.wsgi import utils as wsgi_utils


LOG = logging.getLogger(__name__)


class Resource(object):
    __slots__ = ('_wsgi_conf', '_validate', 'queue_ctrl')

    def __init__(self, _wsgi_conf, validate, queue_controller):
        self._wsgi_conf = _wsgi_conf
        self._validate = validate
        self.queue_ctrl = queue_controller

    def on_get(self, req, resp, project_id, queue_name):
        LOG.debug(_(u'Queue metadata GET - queue: %(queue)s, '
                    u'project: %(project)s'),
                  {'queue': queue_name, 'project': project_id})

        try:
            resp_dict = self.queue_ctrl.get_metadata(queue_name,
                                                     project=project_id)

        except storage_errors.DoesNotExist:
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Queue metadata could not be retrieved.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.content_location = req.path
        resp.body = utils.to_json(resp_dict)
        # status defaults to 200

    def on_put(self, req, resp, project_id, queue_name):
        LOG.debug(_(u'Queue metadata PUT - queue: %(queue)s, '
                    u'project: %(project)s'),
                  {'queue': queue_name, 'project': project_id})

        # Place JSON size restriction before parsing
        if req.content_length > self._wsgi_conf.metadata_max_length:
            description = _(u'Queue metadata size is too large.')
            raise wsgi_errors.HTTPBadRequestBody(description)

        # Deserialize queue metadata
        metadata, = wsgi_utils.filter_stream(req.stream,
                                             req.content_length,
                                             spec=None)

        try:
            self._validate.queue_content(
                metadata, check_size=(
                    self._validate._limits_conf.metadata_size_uplimit <
                    self._wsgi_conf.metadata_max_length))
            self.queue_ctrl.set_metadata(queue_name,
                                         metadata=metadata,
                                         project=project_id)

        except validation.ValidationFailed as ex:
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except storage_errors.QueueDoesNotExist:
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Metadata could not be updated.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204
        resp.location = req.path

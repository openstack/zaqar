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

from marconi.openstack.common.gettextutils import _
import marconi.openstack.common.log as logging
from marconi.queues.storage import errors as storage_errors
from marconi.queues.transport import utils
from marconi.queues.transport.wsgi import errors as wsgi_errors


LOG = logging.getLogger(__name__)


class Resource(object):
    __slots__ = ('_wsgi_conf', '_validate', 'queue_ctrl')

    def __init__(self, _wsgi_conf, validate, queue_controller):
        self._wsgi_conf = _wsgi_conf
        self._validate = validate
        self.queue_ctrl = queue_controller

    def on_get(self, req, resp, project_id, queue_name):
        LOG.debug(u'Queue metadata GET - queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        try:
            resp_dict = self.queue_ctrl.get_metadata(queue_name,
                                                     project=project_id)

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Queue metadata could not be retrieved.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.content_location = req.path
        resp.body = utils.to_json(resp_dict)
        # status defaults to 200

    def on_put(self, req, resp, project_id, queue_name):
        LOG.debug(u'Queue metadata PUT - queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        resp.location = req.path

        description = ("Queue metadata has been deprecated. "
                       "It will be removed completely in the next "
                       "version of the API.")

        # TODO(kgriffs): There is a falcon bug that causes
        # HTTPMethodNotAllowed to always ignore the kwargs, such
        # as "description". Once that is fixed, we can use
        # that class instead of the generic error.
        raise falcon.HTTPError(falcon.HTTP_405, 'Method not allowed',
                               headers={'Allow': 'GET'},
                               description=description)

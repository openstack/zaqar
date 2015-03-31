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

from zaqar.common.api import response
from zaqar.common.api import utils as api_utils
from zaqar.i18n import _
import zaqar.openstack.common.log as logging
from zaqar.storage import errors as storage_errors
from zaqar.transport import validation

LOG = logging.getLogger(__name__)


class Endpoints(object):
    """v1.1 API Endpoints."""

    def __init__(self, storage, control, validate):
        self._queue_controller = storage.queue_controller
        self._message_controller = storage.message_controller
        self._claim_controller = storage.claim_controller

        self._pools_controller = control.pools_controller
        self._flavors_controller = control.flavors_controller

        self._validate = validate

    @api_utils.raises_conn_error
    def queue_list(self, req):
        """Gets a list of queues

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')

        LOG.debug(u'Queue list - project: %(project)s',
                  {'project': project_id})

        kwargs = {}

        if req._body.get('marker') is not None:
            kwargs['marker'] = req._body.get('marker')

        if req._body.get('limit') is not None:
            kwargs['limit'] = req._body.get('limit')

        if req._body.get('detailed') is not None:
            kwargs['detailed'] = req._body.get('detailed')

        try:
            self._validate.queue_listing(**kwargs)
            results = self._queue_controller.list(
                project=project_id, **kwargs)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            error = 'Queues could not be listed.'
            headers = {'status': 503}
            return api_utils.error_response(req, ex, error, headers)

        # Buffer list of queues
        queues = list(next(results))

        # Got some. Prepare the response.
        body = {'queues': queues}
        headers = {'status': 200}

        resp = response.Response(req, body, headers)

        return resp

    @api_utils.raises_conn_error
    def queue_create(self, req):
        """Creates a queue

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        metadata = req._body.get('metadata', {})

        LOG.debug(u'Queue create - queue: %(queue)s, project: %(project)s',
                  {'queue': queue_name,
                   'project': project_id})

        try:
            self._validate.queue_identification(queue_name, project_id)
            self._validate.queue_metadata_length(len(str(metadata)))
            created = self._queue_controller.create(queue_name,
                                                    metadata=metadata,
                                                    project=project_id)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            error = _('Queue %s could not be created.') % queue_name
            headers = {'status': 503}
            return api_utils.error_response(req, ex, headers, error)
        else:
            body = _('Queue %s created.') % queue_name
            headers = {'status': 201} if created else {'status': 204}
            resp = response.Response(req, body, headers)
            return resp

    @api_utils.raises_conn_error
    def queue_delete(self, req):
        """Deletes a queue

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')

        LOG.debug(u'Queue delete - queue: %(queue)s, project: %(project)s',
                  {'queue': queue_name, 'project': project_id})
        try:
            self._queue_controller.delete(queue_name, project=project_id)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            error = _('Queue %s could not be deleted.') % queue_name
            headers = {'status': 503}
            return api_utils.error_response(req, ex, headers, error)
        else:
            body = _('Queue %s removed.') % queue_name
            headers = {'status': 204}
            resp = response.Response(req, body, headers)
            return resp

    @api_utils.raises_conn_error
    def queue_get(self, req):
        """Gets a queue

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')

        LOG.debug(u'Queue get - queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        try:
            resp_dict = self._queue_controller.get(queue_name,
                                                   project=project_id)
        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            error = _('Queue %s does not exist.') % queue_name
            headers = {'status': 404}
            return api_utils.error_response(req, ex, headers, error)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            headers = {'status': 503}
            error = _('Cannot retrieve queue %s.') % queue_name
            return api_utils.error_response(req, ex, headers, error)
        else:
            body = resp_dict
            headers = {'status': 200}
            resp = response.Response(req, body, headers)
            return resp

    @api_utils.raises_conn_error
    def queue_get_stats(self, req):
        """Gets queue stats

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')

        LOG.debug(u'Queue get queue stats - queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        try:
            resp_dict = self._queue_controller.stats(queue_name,
                                                     project=project_id)
            body = resp_dict
        except storage_errors.QueueDoesNotExist as ex:
            LOG.exception(ex)
            resp_dict = {
                'messages': {
                    'claimed': 0,
                    'free': 0,
                    'total': 0
                }
            }
            body = resp_dict
            headers = {'status': 404}
            resp = response.Response(req, body, headers)
            return resp
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            error = _('Cannot retrieve queue %s stats.') % queue_name
            headers = {'status': 503}
            return api_utils.error_response(req, ex, headers, error)
        else:
            headers = {'status': 200}
            resp = response.Response(req, body, headers)
            return resp
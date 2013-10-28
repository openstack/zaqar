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
from marconi.queues.transport import utils
from marconi.queues.transport import validation
from marconi.queues.transport.wsgi import errors as wsgi_errors


LOG = logging.getLogger(__name__)


class ItemResource(object):

    __slots__ = ('queue_controller', 'message_controller')

    def __init__(self, queue_controller, message_controller):
        self.queue_controller = queue_controller
        self.message_controller = message_controller

    def on_put(self, req, resp, project_id, queue_name):
        LOG.debug(_(u'Queue item PUT - queue: %(queue)s, '
                    u'project: %(project)s'),
                  {'queue': queue_name, 'project': project_id})

        try:
            created = self.queue_controller.create(
                queue_name, project=project_id)

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Queue could not be created.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_201 if created else falcon.HTTP_204
        resp.location = req.path

    def on_head(self, req, resp, project_id, queue_name):
        LOG.debug(_(u'Queue item exists - queue: %(queue)s, '
                    u'project: %(project)s'),
                  {'queue': queue_name, 'project': project_id})

        if self.queue_controller.exists(queue_name, project=project_id):
            resp.status = falcon.HTTP_204
        else:
            resp.status = falcon.HTTP_404

        resp.content_location = req.path

    on_get = on_head

    def on_delete(self, req, resp, project_id, queue_name):
        LOG.debug(_(u'Queue item DELETE - queue: %(queue)s, '
                    u'project: %(project)s'),
                  {'queue': queue_name, 'project': project_id})
        try:
            self.queue_controller.delete(queue_name, project=project_id)

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Queue could not be deleted.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204


class CollectionResource(object):

    __slots__ = ('queue_controller', '_validate')

    def __init__(self, validate, queue_controller):
        self.queue_controller = queue_controller
        self._validate = validate

    def on_get(self, req, resp, project_id):

        kwargs = {}

        # NOTE(kgriffs): This syntax ensures that
        # we don't clobber default values with None.
        req.get_param('marker', store=kwargs)
        req.get_param_as_int('limit', store=kwargs)
        req.get_param_as_bool('detailed', store=kwargs)

        try:
            self._validate.queue_listing(**kwargs)
            results = self.queue_controller.list(project=project_id, **kwargs)

        except validation.ValidationFailed as ex:
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Queues could not be listed.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Buffer list of queues
        queues = list(next(results))

        # Check for an empty list
        if len(queues) == 0:
            resp.status = falcon.HTTP_204
            return

        # Got some. Prepare the response.
        kwargs['marker'] = next(results)
        for each_queue in queues:
            each_queue['href'] = req.path + '/' + each_queue['name']

        response_body = {
            'queues': queues,
            'links': [
                {
                    'rel': 'next',
                    'href': req.path + falcon.to_query_str(kwargs)
                }
            ]
        }

        resp.content_location = req.relative_uri
        resp.body = utils.to_json(response_body)
        # status defaults to 200

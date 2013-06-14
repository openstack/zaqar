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

import marconi.openstack.common.log as logging
from marconi.storage import exceptions as storage_exceptions
from marconi import transport
from marconi.transport import helpers
from marconi.transport.wsgi import exceptions as wsgi_exceptions


LOG = logging.getLogger(__name__)


class ItemResource(object):

    __slots__ = ('queue_controller')

    def __init__(self, queue_controller):
        self.queue_controller = queue_controller

    def on_put(self, req, resp, project_id, queue_name):
        # TODO(kgriffs): Migrate this check to input validator middleware
        if req.content_length > transport.MAX_QUEUE_METADATA_SIZE:
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

        # Create or update the queue
        try:
            created = self.queue_controller.upsert(
                queue_name,
                metadata=metadata,
                project=project_id)

        except Exception as ex:
            LOG.exception(ex)
            description = _('Queue could not be created.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_201 if created else falcon.HTTP_204
        resp.location = req.path

    def on_get(self, req, resp, project_id, queue_name):
        try:
            doc = self.queue_controller.get(queue_name, project=project_id)
        except storage_exceptions.DoesNotExist:
            raise falcon.HTTPNotFound()
        except Exception as ex:
            LOG.exception(ex)
            description = _('Queue metdata could not be retrieved.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        resp.content_location = req.relative_uri
        resp.body = helpers.to_json(doc)

    def on_delete(self, req, resp, project_id, queue_name):
        try:
            self.queue_controller.delete(queue_name, project=project_id)

        except Exception as ex:
            LOG.exception(ex)
            description = _('Queue could not be deleted.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204


class CollectionResource(object):

    __slots__ = ('queue_controller')

    def __init__(self, queue_controller):
        self.queue_controller = queue_controller

    def on_get(self, req, resp, project_id):
        # TODO(kgriffs): Optimize
        kwargs = helpers.purge({
            'marker': req.get_param('marker'),
            'limit': req.get_param_as_int('limit'),
            'detailed': req.get_param_as_bool('detailed'),
        })

        try:
            results = self.queue_controller.list(project=project_id, **kwargs)
        except Exception as ex:
            LOG.exception(ex)
            description = _('Queues could not be listed.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        # Buffer list of queues
        queues = list(results.next())

        # Check for an empty list
        if len(queues) == 0:
            resp.status = falcon.HTTP_204
            return

        # Got some. Prepare the response.
        kwargs['marker'] = results.next()
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
        resp.body = helpers.to_json(response_body)
        resp.status = falcon.HTTP_200

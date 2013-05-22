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

import itertools

import falcon

import marconi.openstack.common.log as logging
from marconi.storage import exceptions as storage_exceptions
from marconi.transport import helpers
from marconi.transport.wsgi import exceptions as wsgi_exceptions
from marconi.transport.wsgi import helpers as wsgi_helpers


LOG = logging.getLogger(__name__)
MESSAGE_POST_SPEC = (('ttl', int), ('body', '*'))


class CollectionResource(object):

    __slots__ = ('message_controller')

    def __init__(self, message_controller):
        self.message_controller = message_controller

    def on_post(self, req, resp, project_id, queue_name):
        uuid = req.get_header('Client-ID', required=True)

        # Pull out just the fields we care about
        messages = wsgi_helpers.filter_stream(
            req.stream,
            MESSAGE_POST_SPEC,
            doctype=wsgi_helpers.JSONArray)

        # Verify that at least one message was provided.
        try:
            first_message = messages.next()
        except StopIteration:
            description = _('No messages were provided.')
            raise wsgi_exceptions.HTTPBadRequestBody(description)

        # Hack to make message_controller oblivious to the
        # fact that we just popped the first message.
        messages = itertools.chain((first_message,), messages)

        # Enqueue the messages
        try:
            message_ids = self.message_controller.post(
                queue_name,
                messages=messages,
                project=project_id,
                client_uuid=uuid)

        except storage_exceptions.DoesNotExist:
            raise falcon.HTTPNotFound()
        except Exception as ex:
            LOG.exception(ex)
            description = _('Messages could not be enqueued.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        #TODO(kgriffs): Optimize
        resource = ','.join([id.encode('utf-8') for id in message_ids])
        resp.location = req.path + '/' + resource
        resp.status = falcon.HTTP_201

    def on_get(self, req, resp, project_id, queue_name):
        uuid = req.get_header('Client-ID', required=True)

        #TODO(kgriffs): Optimize
        kwargs = helpers.purge({
            'marker': req.get_param('marker'),
            'limit': req.get_param_as_int('limit'),
            'echo': req.get_param_as_bool('echo'),
        })

        try:
            results = self.message_controller.list(
                queue_name,
                project=project_id,
                client_uuid=uuid,
                **kwargs)

            # Buffer messages
            cursor = results.next()
            messages = list(cursor)

        except storage_exceptions.DoesNotExist:
            raise falcon.HTTPNotFound
        except Exception as ex:
            LOG.exception(ex)
            description = _('Messages could not be listed.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        # Check for no content
        if len(messages) == 0:
            resp.status = falcon.HTTP_204
            return

        # Found some messages, so prepare the response
        kwargs['marker'] = results.next()
        for each_message in messages:
            each_message['href'] = req.path + '/' + each_message['id']
            del each_message['id']

        response_body = {
            'messages': messages,
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


class ItemResource(object):

    __slots__ = ('message_controller')

    def __init__(self, message_controller):
        self.message_controller = message_controller

    def on_get(self, req, resp, project_id, queue_name, message_id):
        try:
            message = self.message_controller.get(
                queue_name,
                message_id=message_id,
                project=project_id)

        except storage_exceptions.DoesNotExist:
            raise falcon.HTTPNotFound()
        except Exception as ex:
            LOG.exception(ex)
            description = _('Message could not be retrieved.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        # Prepare response
        message['href'] = req.path
        del message['id']

        resp.content_location = req.relative_uri
        resp.body = helpers.to_json(message)
        resp.status = falcon.HTTP_200

    def on_delete(self, req, resp, project_id, queue_name, message_id):
        try:
            self.message_controller.delete(
                queue_name,
                message_id=message_id,
                project=project_id,
                claim=req.get_param('claim_id'))

        except storage_exceptions.NotPermitted as ex:
            LOG.exception(ex)
            title = _('Invalid claim')
            description = _('The specified claim either does not '
                            'exist or has expired.')
            raise falcon.HTTPForbidden(title, description)
        except Exception as ex:
            LOG.exception(ex)
            description = _('Message could not be deleted.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        # Alles guete
        resp.status = falcon.HTTP_204

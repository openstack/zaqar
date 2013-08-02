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

from marconi.common import config
import marconi.openstack.common.log as logging
from marconi.storage import exceptions as storage_exceptions
from marconi.transport import helpers
from marconi.transport.wsgi import exceptions as wsgi_exceptions
from marconi.transport.wsgi import helpers as wsgi_helpers


LOG = logging.getLogger(__name__)
CFG = config.namespace('drivers:transport:wsgi').from_options(
    content_max_length=256 * 1024
)

MESSAGE_POST_SPEC = (('ttl', int), ('body', '*'))


class CollectionResource(object):

    __slots__ = ('message_controller')

    def __init__(self, message_controller):
        self.message_controller = message_controller

    #-----------------------------------------------------------------------
    # Helpers
    #-----------------------------------------------------------------------

    def _get_by_id(self, base_path, project_id, queue_name, ids):
        """Returns one or more messages from the queue by ID."""
        try:
            messages = self.message_controller.bulk_get(
                queue_name,
                message_ids=ids,
                project=project_id)

        except Exception as ex:
            LOG.exception(ex)
            description = _('Message could not be retrieved.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        # Prepare response
        messages = list(messages)
        if not messages:
            return None

        base_path += '/'
        for each_message in messages:
            each_message['href'] = base_path + each_message['id']
            del each_message['id']

        return messages

    def _get(self, req, project_id, queue_name):
        uuid = req.get_header('Client-ID', required=True)

        # TODO(kgriffs): Optimize
        kwargs = helpers.purge({
            'marker': req.get_param('marker'),
            'limit': req.get_param_as_int('limit'),
            'echo': req.get_param_as_bool('echo'),
            'include_claimed': req.get_param_as_bool('include_claimed'),
        })

        try:
            results = self.message_controller.list(
                queue_name,
                project=project_id,
                client_uuid=uuid,
                **kwargs)

            # Buffer messages
            cursor = next(results)
            messages = list(cursor)

        except storage_exceptions.DoesNotExist:
            raise falcon.HTTPNotFound()

        except storage_exceptions.MalformedMarker:
            title = _('Invalid query string parameter')
            description = _('The value for the query string '
                            'parameter "marker" could not be '
                            'parsed. We recommend using the '
                            '"next" URI from a previous '
                            'request directly, rather than '
                            'constructing the URI manually. ')

            raise falcon.HTTPBadRequest(title, description)

        except Exception as ex:
            LOG.exception(ex)
            description = _('Messages could not be listed.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        if not messages:
            return None

        # Found some messages, so prepare the response
        kwargs['marker'] = next(results)
        for each_message in messages:
            each_message['href'] = req.path + '/' + each_message['id']
            del each_message['id']

        return {
            'messages': messages,
            'links': [
                {
                    'rel': 'next',
                    'href': req.path + falcon.to_query_str(kwargs)
                }
            ]
        }

    #-----------------------------------------------------------------------
    # Interface
    #-----------------------------------------------------------------------

    def on_post(self, req, resp, project_id, queue_name):
        LOG.debug(_("Messages collection POST - queue:  %(queue)s, "
                    "project: %(project)s") %
                  {"queue": queue_name, "project": project_id})

        uuid = req.get_header('Client-ID', required=True)

        # Place JSON size restriction before parsing
        if req.content_length > CFG.content_max_length:
            description = _('Message collection size is too large.')
            raise wsgi_exceptions.HTTPBadRequestBody(description)

        # Pull out just the fields we care about
        messages = wsgi_helpers.filter_stream(
            req.stream,
            req.content_length,
            MESSAGE_POST_SPEC,
            doctype=wsgi_helpers.JSONArray)

        # Verify that at least one message was provided.
        try:
            first_message = next(messages)
        except StopIteration:
            description = _('No messages were provided.')
            raise wsgi_exceptions.HTTPBadRequestBody(description)

        # Hack to make message_controller oblivious to the
        # fact that we just popped the first message.
        messages = itertools.chain((first_message,), messages)

        # Enqueue the messages
        partial = False

        try:
            message_ids = self.message_controller.post(
                queue_name,
                messages=messages,
                project=project_id,
                client_uuid=uuid)

        except storage_exceptions.DoesNotExist:
            raise falcon.HTTPNotFound()
        except storage_exceptions.MessageConflict as ex:
            LOG.exception(ex)
            partial = True
            message_ids = ex.succeeded_ids

            if not message_ids:
                # TODO(kgriffs): Include error code that is different
                # from the code used in the generic case, below.
                description = _('No messages could be enqueued.')
                raise wsgi_exceptions.HTTPServiceUnavailable(description)

        except Exception as ex:
            LOG.exception(ex)
            description = _('Messages could not be enqueued.')
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        # Prepare the response
        resp.status = falcon.HTTP_201

        ids_value = ','.join(message_ids)
        resp.location = req.path + '?ids=' + ids_value

        hrefs = [req.path + '/' + id for id in message_ids]
        body = {'resources': hrefs, 'partial': partial}
        resp.body = helpers.to_json(body)

    def on_get(self, req, resp, project_id, queue_name):
        LOG.debug(_("Messages collection GET - queue: %(queue)s, "
                    "project: %(project)s") %
                  {"queue": queue_name, "project": project_id})

        resp.content_location = req.relative_uri

        ids = req.get_param_as_list('ids')
        if ids is None:
            response = self._get(req, project_id, queue_name)
        else:
            base_path = req.path + '/messages'
            response = self._get_by_id(base_path, project_id, queue_name, ids)

        if response is None:
            resp.status = falcon.HTTP_204
            return

        resp.body = helpers.to_json(response)

    def on_delete(self, req, resp, project_id, queue_name):
        # NOTE(zyuan): Attempt to delete the whole message collection
        # (without an "ids" parameter) is not allowed
        ids = req.get_param_as_list('ids', required=True)

        try:
            self.message_controller.bulk_delete(
                queue_name,
                message_ids=ids,
                project=project_id)

        except Exception as ex:
            LOG.exception(ex)
            description = 'Messages could not be deleted.'
            raise wsgi_exceptions.HTTPServiceUnavailable(description)

        else:
            resp.status = falcon.HTTP_204


class ItemResource(object):

    __slots__ = ('message_controller')

    def __init__(self, message_controller):
        self.message_controller = message_controller

    def on_get(self, req, resp, project_id, queue_name, message_id):
        LOG.debug(_("Messages item GET - message: %(message)s, "
                    "queue: %(queue)s, project: %(project)s") %
                  {"message": message_id,
                   "queue": queue_name,
                   "project": project_id})
        try:
            message = self.message_controller.get(
                queue_name,
                message_id,
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
        LOG.debug(_("Messages item DELETE - message: %(message)s, "
                    "queue: %(queue)s, project: %(project)s") %
                  {"message": message_id,
                   "queue": queue_name,
                   "project": project_id})
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

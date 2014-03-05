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

from marconi.openstack.common.gettextutils import _
import marconi.openstack.common.log as logging
from marconi.queues.storage import errors as storage_errors
from marconi.queues.transport import utils
from marconi.queues.transport import validation
from marconi.queues.transport.wsgi import errors as wsgi_errors
from marconi.queues.transport.wsgi import utils as wsgi_utils

LOG = logging.getLogger(__name__)

MESSAGE_POST_SPEC = (('ttl', int), ('body', '*'))


class CollectionResource(object):

    __slots__ = ('message_controller', '_wsgi_conf', '_validate')

    def __init__(self, wsgi_conf, validate, message_controller):
        self._wsgi_conf = wsgi_conf
        self._validate = validate
        self.message_controller = message_controller

    #-----------------------------------------------------------------------
    # Helpers
    #-----------------------------------------------------------------------

    def _get_by_id(self, base_path, project_id, queue_name, ids):
        """Returns one or more messages from the queue by ID."""
        try:
            self._validate.message_listing(limit=len(ids))
            messages = self.message_controller.bulk_get(
                queue_name,
                message_ids=ids,
                project=project_id)

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Message could not be retrieved.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

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
        client_uuid = wsgi_utils.get_client_uuid(req)
        kwargs = {}

        # NOTE(kgriffs): This syntax ensures that
        # we don't clobber default values with None.
        req.get_param('marker', store=kwargs)
        req.get_param_as_int('limit', store=kwargs)
        req.get_param_as_bool('echo', store=kwargs)
        req.get_param_as_bool('include_claimed', store=kwargs)

        try:
            self._validate.message_listing(**kwargs)
            results = self.message_controller.list(
                queue_name,
                project=project_id,
                client_uuid=client_uuid,
                **kwargs)

            # Buffer messages
            cursor = next(results)
            messages = list(cursor)

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Messages could not be listed.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

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
        LOG.debug(u'Messages collection POST - queue:  %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        client_uuid = wsgi_utils.get_client_uuid(req)

        try:
            # Place JSON size restriction before parsing
            self._validate.message_length(req.content_length)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        # Pull out just the fields we care about
        messages = wsgi_utils.filter_stream(
            req.stream,
            req.content_length,
            MESSAGE_POST_SPEC,
            doctype=wsgi_utils.JSONArray)

        # Enqueue the messages
        partial = False

        try:
            self._validate.message_posting(messages)

            message_ids = self.message_controller.post(
                queue_name,
                messages=messages,
                project=project_id,
                client_uuid=client_uuid)

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise falcon.HTTPNotFound()

        except storage_errors.MessageConflict as ex:
            LOG.exception(ex)
            partial = True
            message_ids = ex.succeeded_ids

            if not message_ids:
                # TODO(kgriffs): Include error code that is different
                # from the code used in the generic case, below.
                description = _(u'No messages could be enqueued.')
                raise wsgi_errors.HTTPServiceUnavailable(description)

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Messages could not be enqueued.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Prepare the response
        ids_value = ','.join(message_ids)
        resp.location = req.path + '?ids=' + ids_value

        hrefs = [req.path + '/' + id for id in message_ids]
        body = {'resources': hrefs, 'partial': partial}
        resp.body = utils.to_json(body)
        resp.status = falcon.HTTP_201

    def on_get(self, req, resp, project_id, queue_name):
        LOG.debug(u'Messages collection GET - queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        resp.content_location = req.relative_uri

        ids = req.get_param_as_list('ids')
        if ids is None:
            response = self._get(req, project_id, queue_name)
        else:
            response = self._get_by_id(req.path, project_id, queue_name, ids)

        if response is None:
            resp.status = falcon.HTTP_204
            return

        resp.body = utils.to_json(response)
        # status defaults to 200

    def on_delete(self, req, resp, project_id, queue_name):
        # NOTE(zyuan): Attempt to delete the whole message collection
        # (without an "ids" parameter) is not allowed
        ids = req.get_param_as_list('ids', required=True)

        try:
            self._validate.message_listing(limit=len(ids))
            self.message_controller.bulk_delete(
                queue_name,
                message_ids=ids,
                project=project_id)

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Messages could not be deleted.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204


class ItemResource(object):

    __slots__ = ('message_controller')

    def __init__(self, message_controller):
        self.message_controller = message_controller

    def on_get(self, req, resp, project_id, queue_name, message_id):
        LOG.debug(u'Messages item GET - message: %(message)s, '
                  u'queue: %(queue)s, project: %(project)s',
                  {'message': message_id,
                   'queue': queue_name,
                   'project': project_id})
        try:
            message = self.message_controller.get(
                queue_name,
                message_id,
                project=project_id)

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Message could not be retrieved.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Prepare response
        message['href'] = req.path
        del message['id']

        resp.content_location = req.relative_uri
        resp.body = utils.to_json(message)
        # status defaults to 200

    def on_delete(self, req, resp, project_id, queue_name, message_id):
        LOG.debug(u'Messages item DELETE - message: %(message)s, '
                  u'queue: %(queue)s, project: %(project)s',
                  {'message': message_id,
                   'queue': queue_name,
                   'project': project_id})
        try:
            self.message_controller.delete(
                queue_name,
                message_id=message_id,
                project=project_id,
                claim=req.get_param('claim_id'))

        except storage_errors.NotPermitted as ex:
            LOG.exception(ex)
            title = _(u'Unable to delete')
            description = _(u'This message is claimed; it cannot be '
                            u'deleted without a valid claim_id.')
            raise falcon.HTTPForbidden(title, description)

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Message could not be deleted.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Alles guete
        resp.status = falcon.HTTP_204

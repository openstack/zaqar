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
from oslo_log import log as logging
import six

from zaqar.common import decorators
from zaqar.common.transport.wsgi import helpers as wsgi_helpers
from zaqar.i18n import _
from zaqar.storage import errors as storage_errors
from zaqar.transport import acl
from zaqar.transport import utils
from zaqar.transport import validation
from zaqar.transport.wsgi import errors as wsgi_errors
from zaqar.transport.wsgi import utils as wsgi_utils

LOG = logging.getLogger(__name__)


class CollectionResource(object):

    __slots__ = (
        '_message_controller',
        '_queue_controller',
        '_wsgi_conf',
        '_validate',
        '_message_post_spec',
        '_default_message_ttl'
    )

    def __init__(self, wsgi_conf, validate,
                 message_controller, queue_controller,
                 default_message_ttl):

        self._wsgi_conf = wsgi_conf
        self._validate = validate
        self._message_controller = message_controller
        self._queue_controller = queue_controller
        self._default_message_ttl = default_message_ttl

        self._message_post_spec = (
            ('ttl', int, self._default_message_ttl),
            ('body', '*', None),
        )

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    def _get_by_id(self, base_path, project_id, queue_name, ids):
        """Returns one or more messages from the queue by ID."""
        try:
            self._validate.message_listing(limit=len(ids))
            messages = self._message_controller.bulk_get(
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

        messages = [wsgi_utils.format_message_v1_1(m, base_path, m['claim_id'])
                    for m in messages]

        return {'messages': messages}

    def _get(self, req, project_id, queue_name):
        client_uuid = wsgi_helpers.get_client_uuid(req)
        kwargs = {}

        # NOTE(kgriffs): This syntax ensures that
        # we don't clobber default values with None.
        req.get_param('marker', store=kwargs)
        req.get_param_as_int('limit', store=kwargs)
        req.get_param_as_bool('echo', store=kwargs)
        req.get_param_as_bool('include_claimed', store=kwargs)

        try:
            self._validate.message_listing(**kwargs)
            results = self._message_controller.list(
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

        except storage_errors.QueueDoesNotExist as ex:
            LOG.debug(ex)
            messages = None

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Messages could not be listed.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        if not messages:
            messages = []

        else:
            # Found some messages, so prepare the response
            kwargs['marker'] = next(results)
            base_path = req.path.rsplit('/', 1)[0]
            messages = [wsgi_utils.format_message_v1_1(m, base_path,
                                                       m['claim_id'])
                        for m in messages]

        links = []
        if messages:
            links = [
                {
                    'rel': 'next',
                    'href': req.path + falcon.to_query_str(kwargs)
                }
            ]

        return {
            'messages': messages,
            'links': links
        }

    # ----------------------------------------------------------------------
    # Interface
    # ----------------------------------------------------------------------

    @decorators.TransportLog("Messages collection")
    @acl.enforce("messages:create")
    def on_post(self, req, resp, project_id, queue_name):
        client_uuid = wsgi_helpers.get_client_uuid(req)
        try:
            # NOTE(flwang): Replace 'exists' with 'get_metadata' won't impact
            # the performance since both of them will call
            # collection.find_one()
            queue_meta = None
            try:
                queue_meta = self._queue_controller.get_metadata(queue_name,
                                                                 project_id)
            except storage_errors.DoesNotExist as ex:
                self._validate.queue_identification(queue_name, project_id)
                self._queue_controller.create(queue_name, project=project_id)
                # NOTE(flwang): Queue is created in lazy mode, so no metadata
                # set.
                queue_meta = {}

            queue_max_msg_size = queue_meta.get('_max_messages_post_size')
            queue_default_ttl = queue_meta.get('_default_message_ttl')

            # TODO(flwang): To avoid any unexpected regression issue, we just
            # leave the _message_post_spec attribute of class as it's. It
            # should be removed in Newton release.
            if queue_default_ttl:
                message_post_spec = (('ttl', int, queue_default_ttl),
                                     ('body', '*', None),)
            else:
                message_post_spec = (('ttl', int, self._default_message_ttl),
                                     ('body', '*', None),)
            # Place JSON size restriction before parsing
            self._validate.message_length(req.content_length,
                                          max_msg_post_size=queue_max_msg_size)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        # Deserialize and validate the incoming messages
        document = wsgi_utils.deserialize(req.stream, req.content_length)

        if 'messages' not in document:
            description = _(u'No messages were found in the request body.')
            raise wsgi_errors.HTTPBadRequestAPI(description)

        messages = wsgi_utils.sanitize(document['messages'],
                                       message_post_spec,
                                       doctype=wsgi_utils.JSONArray)

        try:
            self._validate.message_posting(messages)

            message_ids = self._message_controller.post(
                queue_name,
                messages=messages,
                project=project_id,
                client_uuid=client_uuid)

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))

        except storage_errors.MessageConflict as ex:
            LOG.exception(ex)
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
        body = {'resources': hrefs}
        resp.body = utils.to_json(body)
        resp.status = falcon.HTTP_201

    @decorators.TransportLog("Messages collection")
    @acl.enforce("messages:get_all")
    def on_get(self, req, resp, project_id, queue_name):
        ids = req.get_param_as_list('ids')

        if ids is None:
            response = self._get(req, project_id, queue_name)

        else:
            response = self._get_by_id(req.path.rsplit('/', 1)[0], project_id,
                                       queue_name, ids)

        if response is None:
            # NOTE(TheSriram): Trying to get a message by id, should
            # return the message if its present, otherwise a 404 since
            # the message might have been deleted.
            msg = _(u'No messages with IDs: {ids} found in the queue {queue} '
                    u'for project {project}.')
            description = msg.format(queue=queue_name, project=project_id,
                                     ids=ids)
            raise wsgi_errors.HTTPNotFound(description)

        else:
            resp.body = utils.to_json(response)
        # status defaults to 200

    @decorators.TransportLog("Messages collection")
    @acl.enforce("messages:delete_all")
    def on_delete(self, req, resp, project_id, queue_name):
        ids = req.get_param_as_list('ids')
        pop_limit = req.get_param_as_int('pop')
        try:
            self._validate.message_deletion(ids, pop_limit)

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        if ids:
            resp.status = self._delete_messages_by_id(queue_name, ids,
                                                      project_id)

        elif pop_limit:
            resp.status, resp.body = self._pop_messages(queue_name,
                                                        project_id,
                                                        pop_limit)

    def _delete_messages_by_id(self, queue_name, ids, project_id):
        try:
            self._message_controller.bulk_delete(
                queue_name,
                message_ids=ids,
                project=project_id)

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Messages could not be deleted.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        return falcon.HTTP_204

    def _pop_messages(self, queue_name, project_id, pop_limit):
        try:
            LOG.debug(u'POP messages - queue: %(queue)s, '
                      u'project: %(project)s',
                      {'queue': queue_name, 'project': project_id})

            messages = self._message_controller.pop(
                queue_name,
                project=project_id,
                limit=pop_limit)

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Messages could not be popped.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Prepare response
        if not messages:
            messages = []
        body = {'messages': messages}
        body = utils.to_json(body)

        return falcon.HTTP_200, body


class ItemResource(object):

    __slots__ = '_message_controller'

    def __init__(self, message_controller):
        self._message_controller = message_controller

    @decorators.TransportLog("Messages item")
    @acl.enforce("messages:get")
    def on_get(self, req, resp, project_id, queue_name, message_id):
        try:
            message = self._message_controller.get(
                queue_name,
                message_id,
                project=project_id)

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Message could not be retrieved.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Prepare response
        message['href'] = req.path
        message = wsgi_utils.format_message_v1_1(message,
                                                 req.path.rsplit('/', 2)[0],
                                                 message['claim_id'])

        resp.body = utils.to_json(message)
        # status defaults to 200

    @decorators.TransportLog("Messages item")
    @acl.enforce("messages:delete")
    def on_delete(self, req, resp, project_id, queue_name, message_id):
        error_title = _(u'Unable to delete')

        try:
            self._message_controller.delete(
                queue_name,
                message_id=message_id,
                project=project_id,
                claim=req.get_param('claim_id'))

        except storage_errors.MessageNotClaimed as ex:
            LOG.debug(ex)
            description = _(u'A claim was specified, but the message '
                            u'is not currently claimed.')
            raise falcon.HTTPBadRequest(error_title, description)

        except storage_errors.ClaimDoesNotExist as ex:
            LOG.debug(ex)
            description = _(u'The specified claim does not exist or '
                            u'has expired.')
            raise falcon.HTTPBadRequest(error_title, description)

        except storage_errors.NotPermitted as ex:
            LOG.debug(ex)
            description = _(u'This message is claimed; it cannot be '
                            u'deleted without a valid claim ID.')
            raise falcon.HTTPForbidden(error_title, description)

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Message could not be deleted.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Alles guete
        resp.status = falcon.HTTP_204

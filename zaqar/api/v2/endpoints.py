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

from stevedore import driver

from oslo_log import log as logging
from oslo_utils import netutils

from zaqar.common.api import errors as api_errors
from zaqar.common.api import response
from zaqar.common.api import utils as api_utils
from zaqar.i18n import _
from zaqar.storage import errors as storage_errors
from zaqar.transport import validation

LOG = logging.getLogger(__name__)


class Endpoints(object):
    """v2 API Endpoints."""

    def __init__(self, storage, control, validate, defaults):
        self._queue_controller = storage.queue_controller
        self._message_controller = storage.message_controller
        self._claim_controller = storage.claim_controller
        self._subscription_controller = storage.subscription_controller

        self._pools_controller = control.pools_controller
        self._flavors_controller = control.flavors_controller

        self._validate = validate

        self._defaults = defaults
        self._subscription_url = None

    # Queues
    @api_utils.on_exception_sends_500
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

        try:
            kwargs = api_utils.get_headers(req)

            self._validate.queue_listing(**kwargs)
            results = self._queue_controller.list(
                project=project_id, **kwargs)
            # Buffer list of queues. Can raise NoPoolFound error.
            queues = list(next(results))
        except (ValueError, validation.ValidationFailed) as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            error = 'Queues could not be listed.'
            headers = {'status': 503}
            return api_utils.error_response(req, ex, headers, error)

        # Got some. Prepare the response.
        body = {'queues': queues}
        headers = {'status': 200}

        return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
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
            self._validate.queue_metadata_putting(metadata)
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
            return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
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
            return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
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
            return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def queue_get_stats(self, req):
        """Gets queue stats

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')

        LOG.debug(u'Get queue stats - queue: %(queue)s, '
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
            return response.Response(req, body, headers)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            error = _('Cannot retrieve queue %s stats.') % queue_name
            headers = {'status': 503}
            return api_utils.error_response(req, ex, headers, error)
        else:
            headers = {'status': 200}
            return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def queue_purge(self, req):
        """Purge queue

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        resource_types = req._body.get('resource_types', ["messages",
                                                          "subscriptions"])

        LOG.debug(u'Purge queue - queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        try:
            pop_limit = 100
            if "messages" in resource_types:
                LOG.debug("Purge all messages under queue %s", queue_name)
                resp = self._pop_messages(req, queue_name,
                                          project_id, pop_limit)
                while resp.get_response()['body']['messages']:
                    resp = self._pop_messages(req, queue_name,
                                              project_id, pop_limit)

            if "subscriptions" in resource_types:
                LOG.debug("Purge all subscriptions under queue %s",
                          queue_name)
                resp = self._subscription_controller.list(queue_name,
                                                          project=project_id)
                subscriptions = list(next(resp))
                for sub in subscriptions:
                    self._subscription_controller.delete(queue_name,
                                                         sub['id'],
                                                         project=project_id)

        except storage_errors.QueueDoesNotExist as ex:
            LOG.exception(ex)
            headers = {'status': 404}
            return api_utils.error_response(req, ex, headers)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            headers = {'status': 503}
            return api_utils.error_response(req, ex, headers)
        else:
            headers = {'status': 204}
            return response.Response(req, {}, headers)

    # Messages
    @api_utils.on_exception_sends_500
    def message_list(self, req):
        """Gets a list of messages on a queue

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')

        LOG.debug(u'Message list - queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        try:
            kwargs = api_utils.get_headers(req)

            client_uuid = api_utils.get_client_uuid(req)

            self._validate.message_listing(**kwargs)
            results = self._message_controller.list(
                queue_name,
                project=project_id,
                client_uuid=client_uuid,
                **kwargs)

            # Buffer messages
            cursor = next(results)
            messages = list(cursor)
        except (ValueError, api_errors.BadRequest,
                validation.ValidationFailed) as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)
        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            headers = {'status': 404}
            return api_utils.error_response(req, ex, headers)

        if messages:
            # Found some messages, so prepare the response
            kwargs['marker'] = next(results)
            messages = [api_utils.format_message(message)
                        for message in messages]

        headers = {'status': 200}
        body = {'messages': messages}

        return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def message_get(self, req):
        """Gets a message from a queue

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        message_id = req._body.get('message_id')

        LOG.debug(u'Message get - message: %(message)s, '
                  u'queue: %(queue)s, project: %(project)s',
                  {'message': message_id,
                   'queue': queue_name,
                   'project': project_id})
        try:
            message = self._message_controller.get(
                queue_name,
                message_id,
                project=project_id)

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            headers = {'status': 404}
            return api_utils.error_response(req, ex, headers)

        # Prepare response
        message = api_utils.format_message(message)

        headers = {'status': 200}
        body = {'messages': message}

        return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def message_get_many(self, req):
        """Gets a set of messages from a queue

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        message_ids = list(req._body.get('message_ids'))

        LOG.debug(u'Message get - queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        try:
            self._validate.message_listing(limit=len(message_ids))
            messages = self._message_controller.bulk_get(
                queue_name,
                message_ids=message_ids,
                project=project_id)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)

        # Prepare response
        messages = list(messages)
        messages = [api_utils.format_message(message)
                    for message in messages]

        headers = {'status': 200}
        body = {'messages': messages}

        return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def message_post(self, req):
        """Post a set of messages to a queue

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')

        LOG.debug(u'Messages post - queue:  %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        messages = req._body.get('messages')

        if messages is None:
            ex = _(u'Invalid request.')
            error = _(u'No messages were found in the request body.')
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers, error)

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

            queue_max_msg_size = queue_meta.get('_max_messages_post_size',
                                                None)
            queue_default_ttl = queue_meta.get('_default_message_ttl')

            # TODO(flwang): To avoid any unexpected regression issue, we just
            # leave the _message_post_spec attribute of class as it's. It
            # should be removed in Newton release.
            if queue_default_ttl:
                _message_post_spec = (('ttl', int, queue_default_ttl),
                                      ('body', '*', None),)
            else:
                _message_post_spec = (('ttl', int, self._defaults.message_ttl),
                                      ('body', '*', None),)
            # Place JSON size restriction before parsing
            self._validate.message_length(len(str(messages)),
                                          max_msg_post_size=queue_max_msg_size)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)

        try:
            messages = api_utils.sanitize(messages,
                                          _message_post_spec,
                                          doctype=list)
        except api_errors.BadRequest as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)

        try:
            client_uuid = api_utils.get_client_uuid(req)

            self._validate.message_posting(messages)

            message_ids = self._message_controller.post(
                queue_name,
                messages=messages,
                project=project_id,
                client_uuid=client_uuid)
        except (api_errors.BadRequest, validation.ValidationFailed) as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)
        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            headers = {'status': 404}
            return api_utils.error_response(req, ex, headers)
        except storage_errors.MessageConflict as ex:
            LOG.exception(ex)
            error = _(u'No messages could be enqueued.')
            headers = {'status': 500}
            return api_utils.error_response(req, ex, headers, error)

        # Prepare the response
        headers = {'status': 201}
        body = {'message_ids': message_ids}

        return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def message_delete(self, req):
        """Delete a message from a queue

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        message_id = req._body.get('message_id')

        LOG.debug(u'Messages item DELETE - message: %(message)s, '
                  u'queue: %(queue)s, project: %(project)s',
                  {'message': message_id,
                   'queue': queue_name,
                   'project': project_id})

        claim_id = req._body.get('claim_id')

        try:
            self._message_controller.delete(
                queue_name,
                message_id=message_id,
                project=project_id,
                claim=claim_id)
        except storage_errors.MessageNotClaimed as ex:
            LOG.debug(ex)
            error = _(u'A claim was specified, but the message '
                      u'is not currently claimed.')
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers, error)
        except storage_errors.ClaimDoesNotExist as ex:
            LOG.debug(ex)
            error = _(u'The specified claim does not exist or '
                      u'has expired.')
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers, error)
        except storage_errors.NotPermitted as ex:
            LOG.debug(ex)
            error = _(u'This message is claimed; it cannot be '
                      u'deleted without a valid claim ID.')
            headers = {'status': 403}
            return api_utils.error_response(req, ex, headers, error)

        headers = {'status': 204}
        body = {}

        return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def message_delete_many(self, req):
        """Deletes a set of messages from a queue

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        message_ids = req._body.get('message_ids')
        pop_limit = req._body.get('pop')

        LOG.debug(u'Messages collection DELETE - queue: %(queue)s,'
                  u'project: %(project)s, messages: %(message_ids)s',
                  {'queue': queue_name, 'project': project_id,
                   'message_ids': message_ids})

        try:
            self._validate.message_deletion(message_ids, pop_limit)

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)

        if message_ids:
            return self._delete_messages_by_id(req, queue_name, message_ids,
                                               project_id)
        elif pop_limit:
            return self._pop_messages(req, queue_name, project_id, pop_limit)

    @api_utils.on_exception_sends_500
    def _delete_messages_by_id(self, req, queue_name, ids, project_id):
        self._message_controller.bulk_delete(queue_name, message_ids=ids,
                                             project=project_id)

        headers = {'status': 204}
        body = {}

        return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def _pop_messages(self, req, queue_name, project_id, pop_limit):

        LOG.debug(u'Pop messages - queue: %(queue)s, project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        messages = self._message_controller.pop(
            queue_name,
            project=project_id,
            limit=pop_limit)

        # Prepare response
        if not messages:
            messages = []

        headers = {'status': 200}
        body = {'messages': messages}

        return response.Response(req, body, headers)

    # Claims
    @api_utils.on_exception_sends_500
    def claim_create(self, req):
        """Creates a claim

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')

        LOG.debug(u'Claims create - queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        self._claim_post_spec = (
            ('ttl', int, self._defaults.claim_ttl),
            ('grace', int, self._defaults.claim_grace),
        )

        # Claim some messages

        # NOTE(vkmc): We build a dict with the ttl and grace
        # This is the metadata the storage is waiting for
        kwargs = api_utils.get_headers(req)
        # Read claim metadata (e.g., ttl) and raise appropriate
        # errors as needed.
        metadata = api_utils.sanitize(kwargs, self._claim_post_spec)

        limit = (None if kwargs.get('limit') is None
                 else kwargs.get('limit'))

        claim_options = {} if limit is None else {'limit': limit}

        try:
            self._validate.claim_creation(metadata, limit=limit)
        except (ValueError, validation.ValidationFailed) as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)

        cid, msgs = self._claim_controller.create(
            queue_name,
            metadata=metadata,
            project=project_id,
            **claim_options)

        # Buffer claimed messages
        # TODO(vkmc): optimize, along with serialization (below)
        resp_msgs = list(msgs)

        # Serialize claimed messages, if any. This logic assumes
        # the storage driver returned well-formed messages.
        if len(resp_msgs) != 0:
            resp_msgs = [api_utils.format_message(msg, cid)
                         for msg in resp_msgs]

            headers = {'status': 201}
            body = {'claim_id': cid, 'messages': resp_msgs}
        else:
            headers = {'status': 204}
            body = {'claim_id': cid}

        return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def claim_get(self, req):
        """Gets a claim

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        claim_id = req._body.get('claim_id')

        LOG.debug(u'Claim get - claim: %(claim_id)s, '
                  u'queue: %(queue_name)s, project: %(project_id)s',
                  {'queue_name': queue_name,
                   'project_id': project_id,
                   'claim_id': claim_id})
        try:
            meta, msgs = self._claim_controller.get(
                queue_name,
                claim_id=claim_id,
                project=project_id)

            # Buffer claimed messages
            # TODO(vkmc): Optimize along with serialization (see below)
            meta['messages'] = list(msgs)
        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            error = _('Claim %s does not exist.') % claim_id
            headers = {'status': 404}
            return api_utils.error_response(req, ex, headers, error)

        # Serialize claimed messages
        # TODO(vkmc): Optimize
        meta['messages'] = [api_utils.format_message(msg, claim_id)
                            for msg in meta['messages']]

        del meta['id']

        headers = {'status': 200}
        body = meta

        return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def claim_update(self, req):
        """Updates a claim

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        claim_id = req._body.get('claim_id')

        LOG.debug(u'Claim update - claim: %(claim_id)s, '
                  u'queue: %(queue_name)s, project:%(project_id)s',
                  {'queue_name': queue_name,
                   'project_id': project_id,
                   'claim_id': claim_id})

        self._claim_patch_spec = (
            ('ttl', int, self._defaults.claim_ttl),
            ('grace', int, self._defaults.claim_grace),
        )

        # Read claim metadata (e.g., TTL) and raise appropriate
        # HTTP errors as needed.
        metadata = api_utils.sanitize(req._body, self._claim_patch_spec)

        try:
            self._validate.claim_updating(metadata)
            self._claim_controller.update(queue_name,
                                          claim_id=claim_id,
                                          metadata=metadata,
                                          project=project_id)
            headers = {'status': 204}
            body = _('Claim %s updated.') % claim_id
            return response.Response(req, body, headers)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)
        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            error = _('Claim %s does not exist.') % claim_id
            headers = {'status': 404}
            return api_utils.error_response(req, ex, headers, error)

    @api_utils.on_exception_sends_500
    def claim_delete(self, req):
        """Deletes a claim

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        claim_id = req._body.get('claim_id')

        LOG.debug(u'Claim delete - claim: %(claim_id)s, '
                  u'queue: %(queue_name)s, project: %(project_id)s',
                  {'queue_name': queue_name,
                   'project_id': project_id,
                   'claim_id': claim_id})

        self._claim_controller.delete(queue_name,
                                      claim_id=claim_id,
                                      project=project_id)

        headers = {'status': 204}
        body = _('Claim %s deleted.') % claim_id

        return response.Response(req, body, headers)

    # Subscriptions
    @api_utils.on_exception_sends_500
    def subscription_list(self, req):
        """List all subscriptions for a queue.

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')

        LOG.debug(u'Subscription list - project: %(project)s',
                  {'project': project_id})

        try:
            kwargs = api_utils.get_headers(req)

            self._validate.subscription_listing(**kwargs)
            results = self._subscription_controller.list(
                queue_name, project=project_id, **kwargs)
            # Buffer list of subscriptions. Can raise NoPoolFound error.
            subscriptions = list(next(results))
        except (ValueError, validation.ValidationFailed) as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            error = 'Subscriptions could not be listed.'
            headers = {'status': 503}
            return api_utils.error_response(req, ex, headers, error)

        # Got some. Prepare the response.
        body = {'subscriptions': subscriptions}
        headers = {'status': 200}

        return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def subscription_create(self, req, subscriber):
        """Create a subscription for a queue.

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        options = req._body.get('options', {})
        ttl = req._body.get('ttl', self._defaults.subscription_ttl)

        LOG.debug(
            u'Subscription create - queue: %(queue)s, project: %(project)s',
            {'queue': queue_name,
             'project': project_id})

        try:
            url = netutils.urlsplit(subscriber)
            mgr = driver.DriverManager('zaqar.notification.tasks', url.scheme,
                                       invoke_on_load=True)
            req_data = req._env.copy()
            mgr.driver.register(subscriber, options, ttl, project_id, req_data)

            data = {'subscriber': subscriber,
                    'options': options,
                    'ttl': ttl}
            self._validate.subscription_posting(data)
            self._validate.queue_identification(queue_name, project_id)
            if not self._queue_controller.exists(queue_name, project_id):
                self._queue_controller.create(queue_name, project=project_id)
            created = self._subscription_controller.create(queue_name,
                                                           subscriber,
                                                           data['ttl'],
                                                           data['options'],
                                                           project=project_id)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            headers = {'status': 400}
            return api_utils.error_response(req, ex, headers)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            error = _('Subscription %s could not be created.') % queue_name
            headers = {'status': 503}
            return api_utils.error_response(req, ex, headers, error)
        else:
            if created:
                msg = _('Subscription %s created.') % queue_name
                body = {'subscription_id': str(created), 'message': msg}
                headers = {'status': 201}
            else:
                body = _('Subscription %s not created.') % queue_name
                headers = {'status': 409}
            return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def subscription_delete(self, req):
        """Delete a specific subscription by ID.

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        subscription_id = req._body.get('subscription_id')

        LOG.debug(
            u'Subscription delete - queue: %(queue)s, project: %(project)s',
            {'queue': queue_name, 'project': project_id})
        try:
            self._subscription_controller.delete(queue_name,
                                                 subscription_id,
                                                 project=project_id)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            error = _('Subscription %(subscription)s for queue %(queue)s '
                      'could not be deleted.') % {
                'subscription': subscription_id, 'queue': queue_name}
            headers = {'status': 503}
            return api_utils.error_response(req, ex, headers, error)
        else:
            body = _('Subscription %s removed.') % subscription_id
            headers = {'status': 204}
            return response.Response(req, body, headers)

    @api_utils.on_exception_sends_500
    def subscription_get(self, req):
        """Retrieve details about an existing subscription.

        :param req: Request instance ready to be sent.
        :type req: `api.common.Request`
        :return: resp: Response instance
        :type: resp: `api.common.Response`
        """
        project_id = req._headers.get('X-Project-ID')
        queue_name = req._body.get('queue_name')
        subscription_id = req._body.get('subscription_id')

        LOG.debug(u'Subscription get - queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        try:
            resp_dict = self._subscription_controller.get(queue_name,
                                                          subscription_id,
                                                          project=project_id)
        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            error = _('Subscription %(subscription)s for queue %(queue)s '
                      'does not exist.') % {
                'subscription': subscription_id, 'queue': queue_name}
            headers = {'status': 404}
            return api_utils.error_response(req, ex, headers, error)
        except storage_errors.ExceptionBase as ex:
            LOG.exception(ex)
            headers = {'status': 503}
            error = _('Cannot retrieve subscription %s.') % subscription_id
            return api_utils.error_response(req, ex, headers, error)
        else:
            body = resp_dict
            headers = {'status': 200}
            return response.Response(req, body, headers)

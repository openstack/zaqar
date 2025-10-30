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

import copy
import falcon
from oslo_log import log as logging

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar.storage import errors as storage_errors
from zaqar.transport import acl
from zaqar.transport import utils
from zaqar.transport import validation
from zaqar.transport.wsgi import errors as wsgi_errors
from zaqar.transport.wsgi import utils as wsgi_utils

LOG = logging.getLogger(__name__)


def _get_reserved_metadata(validate):
    _reserved_metadata = ['max_messages_post_size', 'default_message_ttl',
                          'default_message_delay']
    reserved_metadata = {
        '_%s' % meta:
            validate.get_limit_conf_value(meta)
        for meta in _reserved_metadata
    }

    for metadata in ['_dead_letter_queue', '_dead_letter_queue_messages_ttl',
                     '_max_claim_count']:
        reserved_metadata.update({metadata: None})
    reserved_metadata.update({'_enable_encrypt_messages': False})
    return reserved_metadata


class ItemResource:

    __slots__ = ('_validate', '_queue_controller', '_message_controller',
                 '_reserved_metadata')

    def __init__(self, validate, queue_controller, message_controller):
        self._validate = validate
        self._queue_controller = queue_controller
        self._message_controller = message_controller

    @decorators.TransportLog("Queues item")
    @acl.enforce("queues:get")
    def on_get(self, req, resp, project_id, queue_name):
        try:
            resp_dict = self._queue_controller.get(queue_name,
                                                   project=project_id)
            for meta, value in _get_reserved_metadata(self._validate).items():
                if not resp_dict.get(meta):
                    resp_dict[meta] = value
        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(str(ex))

        except Exception:
            description = _('Queue metadata could not be retrieved.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.text = utils.to_json(resp_dict)
        # status defaults to 200

    @decorators.TransportLog("Queues item")
    @acl.enforce("queues:create")
    def on_put(self, req, resp, project_id, queue_name):
        try:
            # Place JSON size restriction before parsing
            self._validate.queue_metadata_length(req.content_length)
            # Deserialize queue metadata
            metadata = None
            if req.content_length:
                document = wsgi_utils.deserialize(req.stream,
                                                  req.content_length)
                metadata = wsgi_utils.sanitize(document)
            self._validate.queue_metadata_putting(metadata)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(str(ex))

        try:
            created = self._queue_controller.create(queue_name,
                                                    metadata=metadata,
                                                    project=project_id)

        except storage_errors.FlavorDoesNotExist as ex:
            LOG.exception('Flavor "%s" does not exist', queue_name)
            raise wsgi_errors.HTTPBadRequestAPI(str(ex))
        except Exception:
            description = _('Queue could not be created.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_201 if created else falcon.HTTP_204
        resp.location = req.path

    @decorators.TransportLog("Queues item")
    @acl.enforce("queues:delete")
    def on_delete(self, req, resp, project_id, queue_name):
        LOG.debug('Queue item DELETE - queue: %(queue)s, '
                  'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})
        try:
            self._queue_controller.delete(queue_name, project=project_id)

        except Exception:
            description = _('Queue could not be deleted.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204

    @decorators.TransportLog("Queues item")
    @acl.enforce("queues:update")
    def on_patch(self, req, resp, project_id, queue_name):
        """Allows one to update a queue's metadata.

        This method expects the user to submit a JSON object. There is also
        strict format checking through the use of
        jsonschema. Appropriate errors are returned in each case for
        badly formatted input.

        :returns: HTTP | 200,400,409,503
        """
        LOG.debug('PATCH queue - name: %s', queue_name)

        try:
            # Place JSON size restriction before parsing
            self._validate.queue_metadata_length(req.content_length)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestBody(str(ex))

        # NOTE(flwang): See below link to get more details about draft 10,
        # tools.ietf.org/html/draft-ietf-appsawg-json-patch-10
        content_types = {
            'application/openstack-messaging-v2.0-json-patch': 10,
        }

        if req.content_type not in content_types:
            headers = {'Accept-Patch':
                       ', '.join(sorted(content_types.keys()))}
            msg = _("Accepted media type for PATCH: %s.")
            LOG.debug(msg, headers)
            raise wsgi_errors.HTTPUnsupportedMediaType(msg % headers)

        if req.content_length:
            try:
                changes = utils.read_json(req.stream, req.content_length)
                changes = wsgi_utils.sanitize(changes, doctype=list)
            except utils.MalformedJSON as ex:
                LOG.debug(ex)
                description = _('Request body could not be parsed.')
                raise wsgi_errors.HTTPBadRequestBody(description)

            except utils.OverflowedJSONInteger as ex:
                LOG.debug(ex)
                description = _('JSON contains integer that is too large.')
                raise wsgi_errors.HTTPBadRequestBody(description)

            except Exception:
                # Error while reading from the network/server
                description = _('Request body could not be read.')
                LOG.exception(description)
                raise wsgi_errors.HTTPServiceUnavailable(description)
        else:
            msg = _("PATCH body could not be empty for update.")
            LOG.debug(msg)
            raise wsgi_errors.HTTPBadRequestBody(msg)

        try:
            changes = self._validate.queue_patching(req, changes)

            # NOTE(Eva-i): using 'get_metadata' instead of 'get', so
            # QueueDoesNotExist error will be thrown in case of non-existent
            # queue.
            metadata = self._queue_controller.get_metadata(queue_name,
                                                           project=project_id)
            reserved_metadata = _get_reserved_metadata(self._validate)
            for change in changes:
                change_method_name = '_do_%s' % change['op']
                change_method = getattr(self, change_method_name)
                change_method(req, metadata, reserved_metadata, change)

            self._validate.queue_metadata_putting(metadata)

            self._queue_controller.set_metadata(queue_name,
                                                metadata,
                                                project_id)
        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(str(ex))
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestBody(str(ex))
        except wsgi_errors.HTTPConflict:
            raise
        except Exception:
            description = _('Queue could not be updated.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)
        for meta, value in _get_reserved_metadata(self._validate).items():
            if not metadata.get(meta):
                metadata[meta] = value
        resp.text = utils.to_json(metadata)

    def _do_replace(self, req, metadata, reserved_metadata, change):
        path = change['path']
        path_child = path[1]
        value = change['value']
        if path_child in metadata or path_child in reserved_metadata:
            metadata[path_child] = value
        else:
            msg = _("Can't replace non-existent object %s.")
            raise wsgi_errors.HTTPConflict(msg % path_child)

    def _do_add(self, req, metadata, reserved_metadata, change):
        path = change['path']
        path_child = path[1]
        value = change['value']
        metadata[path_child] = value

    def _do_remove(self, req, metadata, reserved_metadata, change):
        path = change['path']
        path_child = path[1]
        if path_child in metadata:
            metadata.pop(path_child)
        elif path_child not in reserved_metadata:
            msg = _("Can't remove non-existent object %s.")
            raise wsgi_errors.HTTPConflict(msg % path_child)


class CollectionResource:

    __slots__ = ('_queue_controller', '_validate', '_reserved_metadata')

    def __init__(self, validate, queue_controller):
        self._queue_controller = queue_controller
        self._validate = validate

    def _queue_list(self, project_id, path, kfilter, **kwargs):
        try:
            self._validate.queue_listing(**kwargs)
            with_count = kwargs.pop('with_count', False)
            results = self._queue_controller.list(project=project_id,
                                                  kfilter=kfilter, **kwargs)

            # Buffer list of queues
            queues = list(next(results))

            total_number = None
            if with_count:
                total_number = self._queue_controller.calculate_resource_count(
                    project=project_id)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(str(ex))

        except Exception:
            description = _('Queues could not be listed.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Got some. Prepare the response.
        kwargs['marker'] = next(results) or kwargs.get('marker', '')
        reserved_metadata = _get_reserved_metadata(self._validate).items()
        for each_queue in queues:
            each_queue['href'] = path + '/' + each_queue['name']
            if kwargs.get('detailed'):
                for meta, value in reserved_metadata:
                    if not each_queue.get('metadata', {}).get(meta):
                        each_queue['metadata'][meta] = value

        return queues, kwargs['marker'], total_number

    def _on_get_with_kfilter(self, req, resp, project_id, kfilter={}):
        kwargs = {}

        # NOTE(kgriffs): This syntax ensures that
        # we don't clobber default values with None.
        req.get_param('marker', store=kwargs)
        req.get_param_as_int('limit', store=kwargs)
        req.get_param_as_bool('detailed', store=kwargs)
        req.get_param('name', store=kwargs)
        req.get_param_as_bool('with_count', store=kwargs)

        queues, marker, total_number = self._queue_list(project_id,
                                                        req.path, kfilter,
                                                        **kwargs)

        links = []
        kwargs['marker'] = marker
        if queues:
            links = [
                {
                    'rel': 'next',
                    'href': req.path + falcon.to_query_str(kwargs)
                }
            ]

        response_body = {
            'queues': queues,
            'links': links
        }

        if total_number:
            response_body['count'] = total_number

        resp.text = utils.to_json(response_body)
        # status defaults to 200

    @decorators.TransportLog("Queues collection")
    @acl.enforce("queues:get_all")
    def on_get(self, req, resp, project_id):
        field = ('marker', 'limit', 'detailed', 'name', 'with_count')
        kfilter = copy.deepcopy(req.params)

        for key in req.params.keys():
            if key in field:
                kfilter.pop(key)

        kfilter = kfilter if len(kfilter) > 0 else {}
        for key in kfilter.keys():
            # Since we get the filter value from URL, so need to
            # turn the string to integer if using integer filter value.
            try:
                kfilter[key] = int(kfilter[key])
            except ValueError:
                continue
        self._on_get_with_kfilter(req, resp, project_id, kfilter)
        # status defaults to 200

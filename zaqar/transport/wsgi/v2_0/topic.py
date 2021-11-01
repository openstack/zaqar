# Copyright (c) 2019 Rackspace, Inc.
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

    return reserved_metadata


class ItemResource(object):

    __slots__ = ('_validate', '_topic_controller', '_message_controller',
                 '_reserved_metadata')

    def __init__(self, validate, topic_controller, message_controller):
        self._validate = validate
        self._topic_controller = topic_controller
        self._message_controller = message_controller

    @decorators.TransportLog("Topics item")
    @acl.enforce("topics:get")
    def on_get(self, req, resp, project_id, topic_name):
        try:
            resp_dict = self._topic_controller.get(topic_name,
                                                   project=project_id)
            for meta, value in _get_reserved_metadata(self._validate).items():
                if not resp_dict.get(meta):
                    resp_dict[meta] = value
        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(str(ex))

        except Exception:
            description = _(u'Topic metadata could not be retrieved.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.body = utils.to_json(resp_dict)
        # status defaults to 200

    @decorators.TransportLog("Topics item")
    @acl.enforce("topics:create")
    def on_put(self, req, resp, project_id, topic_name):
        try:
            # Place JSON size restriction before parsing
            self._validate.queue_metadata_length(req.content_length)
            # Deserialize Topic metadata
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
            created = self._topic_controller.create(topic_name,
                                                    metadata=metadata,
                                                    project=project_id)

        except storage_errors.FlavorDoesNotExist as ex:
            LOG.exception('Flavor "%s" does not exist', topic_name)
            raise wsgi_errors.HTTPBadRequestAPI(str(ex))
        except Exception:
            description = _(u'Topic could not be created.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_201 if created else falcon.HTTP_204
        resp.location = req.path

    @decorators.TransportLog("Topics item")
    @acl.enforce("topics:delete")
    def on_delete(self, req, resp, project_id, topic_name):
        LOG.debug(u'Topic item DELETE - topic: %(topic)s, '
                  u'project: %(project)s',
                  {'topic': topic_name, 'project': project_id})
        try:
            self._topic_controller.delete(topic_name, project=project_id)

        except Exception:
            description = _(u'Topic could not be deleted.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204

    @decorators.TransportLog("Topics item")
    @acl.enforce("topics:update")
    def on_patch(self, req, resp, project_id, topic_name):
        """Allows one to update a topic's metadata.

        This method expects the user to submit a JSON object. There is also
        strict format checking through the use of
        jsonschema. Appropriate errors are returned in each case for
        badly formatted input.

        :returns: HTTP | 200,400,409,503
        """
        LOG.debug(u'PATCH topic - name: %s', topic_name)

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
                description = _(u'Request body could not be parsed.')
                raise wsgi_errors.HTTPBadRequestBody(description)

            except utils.OverflowedJSONInteger as ex:
                LOG.debug(ex)
                description = _(u'JSON contains integer that is too large.')
                raise wsgi_errors.HTTPBadRequestBody(description)

            except Exception:
                # Error while reading from the network/server
                description = _(u'Request body could not be read.')
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
            metadata = self._topic_controller.get_metadata(topic_name,
                                                           project=project_id)
            reserved_metadata = _get_reserved_metadata(self._validate)
            for change in changes:
                change_method_name = '_do_%s' % change['op']
                change_method = getattr(self, change_method_name)
                change_method(req, metadata, reserved_metadata, change)

            self._validate.queue_metadata_putting(metadata)

            self._topic_controller.set_metadata(topic_name,
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
            description = _(u'Topic could not be updated.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)
        for meta, value in _get_reserved_metadata(self._validate).items():
            if not metadata.get(meta):
                metadata[meta] = value
        resp.body = utils.to_json(metadata)

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


class CollectionResource(object):

    __slots__ = ('_topic_controller', '_validate', '_reserved_metadata')

    def __init__(self, validate, topic_controller):
        self._topic_controller = topic_controller
        self._validate = validate

    def _topic_list(self, project_id, path, kfilter, **kwargs):
        try:
            self._validate.queue_listing(**kwargs)
            results = self._topic_controller.list(project=project_id,
                                                  kfilter=kfilter, **kwargs)

            # Buffer list of topics
            topics = list(next(results))

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(str(ex))

        except Exception:
            description = _(u'Topics could not be listed.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Got some. Prepare the response.
        kwargs['marker'] = next(results) or kwargs.get('marker', '')
        reserved_metadata = _get_reserved_metadata(self._validate).items()
        for each_topic in topics:
            each_topic['href'] = path + '/' + each_topic['name']
            if kwargs.get('detailed'):
                for meta, value in reserved_metadata:
                    if not each_topic.get('metadata', {}).get(meta):
                        each_topic['metadata'][meta] = value

        return topics, kwargs['marker']

    def _on_get_with_kfilter(self, req, resp, project_id, kfilter={}):
        kwargs = {}

        # NOTE(kgriffs): This syntax ensures that
        # we don't clobber default values with None.
        req.get_param('marker', store=kwargs)
        req.get_param_as_int('limit', store=kwargs)
        req.get_param_as_bool('detailed', store=kwargs)
        req.get_param('name', store=kwargs)

        topics, marker = self._topic_list(project_id,
                                          req.path, kfilter, **kwargs)

        links = []
        kwargs['marker'] = marker
        if topics:
            links = [
                {
                    'rel': 'next',
                    'href': req.path + falcon.to_query_str(kwargs)
                }
            ]

        response_body = {
            'topics': topics,
            'links': links
        }

        resp.body = utils.to_json(response_body)
        # status defaults to 200

    @decorators.TransportLog("Topics collection")
    @acl.enforce("topics:get_all")
    def on_get(self, req, resp, project_id):
        field = ('marker', 'limit', 'detailed', 'name')
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

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
from zaqar.i18n import _
from zaqar.storage import errors as storage_errors
from zaqar.transport import utils
from zaqar.transport import validation
from zaqar.transport.wsgi import errors as wsgi_errors
from zaqar.transport.wsgi import utils as wsgi_utils

LOG = logging.getLogger(__name__)

CLAIM_POST_SPEC = (('ttl', int, None), ('grace', int, None))
CLAIM_PATCH_SPEC = (('ttl', int, None), ('grace', int, 0))


class Resource(object):

    __slots__ = ('_claim_controller', '_validate')

    def __init__(self, wsgi_conf, validate, claim_controller):
        self._claim_controller = claim_controller
        self._validate = validate


class CollectionResource(Resource):

    @decorators.TransportLog("Claims collection")
    def on_post(self, req, resp, project_id, queue_name):
        # Check for an explicit limit on the # of messages to claim
        limit = req.get_param_as_int('limit')
        claim_options = {} if limit is None else {'limit': limit}

        # Read claim metadata (e.g., TTL) and raise appropriate
        # HTTP errors as needed.
        document = wsgi_utils.deserialize(req.stream, req.content_length)
        metadata = wsgi_utils.sanitize(document, CLAIM_POST_SPEC)

        # Claim some messages
        try:
            self._validate.claim_creation(metadata, limit=limit)
            cid, msgs = self._claim_controller.create(
                queue_name,
                metadata=metadata,
                project=project_id,
                **claim_options)

            # Buffer claimed messages
            # TODO(kgriffs): optimize, along with serialization (below)
            resp_msgs = list(msgs)

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Claim could not be created.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Serialize claimed messages, if any. This logic assumes
        # the storage driver returned well-formed messages.
        if len(resp_msgs) != 0:
            resp_msgs = [wsgi_utils.format_message_v1(
                msg, req.path.rpartition('/')[0], cid) for msg in resp_msgs]

            resp.location = req.path + '/' + cid
            resp.body = utils.to_json(resp_msgs)
            resp.status = falcon.HTTP_201
        else:
            resp.status = falcon.HTTP_204


class ItemResource(Resource):

    __slots__ = ('_claim_controller', '_validate')

    def __init__(self, wsgi_conf, validate, claim_controller):
        self._claim_controller = claim_controller
        self._validate = validate

    @decorators.TransportLog("Claim item")
    def on_get(self, req, resp, project_id, queue_name, claim_id):
        try:
            meta, msgs = self._claim_controller.get(
                queue_name,
                claim_id=claim_id,
                project=project_id)

            # Buffer claimed messages
            # TODO(kgriffs): Optimize along with serialization (see below)
            meta['messages'] = list(msgs)

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))
        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Claim could not be queried.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Serialize claimed messages
        # TODO(kgriffs): Optimize
        meta['messages'] = [wsgi_utils.format_message_v1(
            msg, req.path.rsplit('/', 2)[0], meta['id'])
            for msg in meta['messages']]

        meta['href'] = req.path
        del meta['id']

        resp.content_location = req.relative_uri
        resp.body = utils.to_json(meta)
        # status defaults to 200

    @decorators.TransportLog("Claim item")
    def on_patch(self, req, resp, project_id, queue_name, claim_id):
        # Read claim metadata (e.g., TTL) and raise appropriate
        # HTTP errors as needed.
        document = wsgi_utils.deserialize(req.stream, req.content_length)
        metadata = wsgi_utils.sanitize(document, CLAIM_PATCH_SPEC)

        try:
            self._validate.claim_updating(metadata)
            self._claim_controller.update(queue_name,
                                          claim_id=claim_id,
                                          metadata=metadata,
                                          project=project_id)

            resp.status = falcon.HTTP_204

        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Claim could not be updated.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

    @decorators.TransportLog("Claim item")
    def on_delete(self, req, resp, project_id, queue_name, claim_id):
        try:
            self._claim_controller.delete(queue_name,
                                          claim_id=claim_id,
                                          project=project_id)

            resp.status = falcon.HTTP_204

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Claim could not be deleted.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

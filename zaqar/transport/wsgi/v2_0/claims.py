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
from zaqar.transport import acl
from zaqar.transport import utils
from zaqar.transport import validation
from zaqar.transport.wsgi import errors as wsgi_errors
from zaqar.transport.wsgi import utils as wsgi_utils

LOG = logging.getLogger(__name__)


class CollectionResource(object):
    __slots__ = (
        '_claim_controller',
        '_validate',
        '_claim_post_spec',
        '_default_meta',
    )

    def __init__(self, wsgi_conf, validate, claim_controller,
                 default_claim_ttl, default_grace_ttl):

        self._claim_controller = claim_controller
        self._validate = validate

        self._claim_post_spec = (
            ('ttl', int, default_claim_ttl),
            ('grace', int, default_grace_ttl),
        )

        # NOTE(kgriffs): Create this once up front, rather than creating
        # a new dict every time, for the sake of performance.
        self._default_meta = {
            'ttl': default_claim_ttl,
            'grace': default_grace_ttl,
        }

    @decorators.TransportLog("Claims collection")
    @acl.enforce("claims:create")
    def on_post(self, req, resp, project_id, queue_name):
        # Check for an explicit limit on the # of messages to claim
        limit = req.get_param_as_int('limit')
        claim_options = {} if limit is None else {'limit': limit}

        # NOTE(kgriffs): Clients may or may not actually include the
        # Content-Length header when the body is empty; the following
        # check works for both 0 and None.
        if not req.content_length:
            # No values given, so use defaults
            metadata = self._default_meta
        else:
            # Read claim metadata (e.g., TTL) and raise appropriate
            # HTTP errors as needed.
            document = wsgi_utils.deserialize(req.stream, req.content_length)
            metadata = wsgi_utils.sanitize(document, self._claim_post_spec)

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
            base_path = req.path.rpartition('/')[0]
            resp_msgs = [wsgi_utils.format_message_v1_1(msg, base_path, cid)
                         for msg in resp_msgs]

            resp.location = req.path + '/' + cid
            resp.body = utils.to_json({'messages': resp_msgs})
            resp.status = falcon.HTTP_201
        else:
            resp.status = falcon.HTTP_204


class ItemResource(object):

    __slots__ = ('_claim_controller', '_validate', '_claim_patch_spec')

    def __init__(self, wsgi_conf, validate, claim_controller,
                 default_claim_ttl, default_grace_ttl):
        self._claim_controller = claim_controller
        self._validate = validate

        self._claim_patch_spec = (
            ('ttl', int, default_claim_ttl),
            ('grace', int, default_grace_ttl),
        )

    @decorators.TransportLog("Claims item")
    @acl.enforce("claims:get")
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
        base_path = req.path.rsplit('/', 2)[0]
        meta['messages'] = [wsgi_utils.format_message_v1_1(msg, base_path,
                                                           claim_id)
                            for msg in meta['messages']]

        meta['href'] = req.path
        del meta['id']

        resp.body = utils.to_json(meta)
        # status defaults to 200

    @decorators.TransportLog("Claims item")
    @acl.enforce("claims:update")
    def on_patch(self, req, resp, project_id, queue_name, claim_id):
        # Read claim metadata (e.g., TTL) and raise appropriate
        # HTTP errors as needed.
        document = wsgi_utils.deserialize(req.stream, req.content_length)
        metadata = wsgi_utils.sanitize(document, self._claim_patch_spec)

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

    @decorators.TransportLog("Claims item")
    @acl.enforce("claims:delete")
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

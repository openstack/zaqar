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

import logging

import falcon

from marconi.storage import exceptions
from marconi import transport
from marconi.transport import helpers


LOG = logging.getLogger(__name__)


class ItemResource(object):

    __slots__ = ('queue_ctrl')

    def __init__(self, queue_controller):
        self.queue_ctrl = queue_controller

    def on_put(self, req, resp, tenant_id, queue_name):
        if req.content_length > transport.MAX_QUEUE_METADATA_SIZE:
            raise falcon.HTTPBadRequest(_('Bad request'),
                                        _('Queue metadata size is too large.'))

        if req.content_length is None or req.content_length == 0:
            raise falcon.HTTPBadRequest(_('Bad request'),
                                        _('Missing queue metadata.'))

        try:
            metadata = _filtered(helpers.read_json(req.stream))
            created = self.queue_ctrl.upsert(queue_name,
                                             metadata=metadata,
                                             tenant=tenant_id)
        except helpers.MalformedJSON:
            raise falcon.HTTPBadRequest(_('Bad request'),
                                        _('Malformed queue metadata.'))

        except Exception as ex:
            LOG.error(ex)
            title = _('Service temporarily unavailable')
            msg = _('Please try again in a few seconds.')
            raise falcon.HTTPServiceUnavailable(title, msg, 30)

        resp.status = falcon.HTTP_201 if created else falcon.HTTP_204
        resp.location = req.path

    def on_get(self, req, resp, tenant_id, queue_name):
        try:
            doc = self.queue_ctrl.get(queue_name,
                                      tenant=tenant_id)
        except exceptions.DoesNotExist:
            raise falcon.HTTPNotFound

        except Exception as ex:
            LOG.error(ex)
            title = _('Service temporarily unavailable')
            msg = _('Please try again in a few seconds.')
            raise falcon.HTTPServiceUnavailable(title, msg, 30)

        try:
            resp.content_location = req.path
            resp.body = helpers.to_json(doc)
        except TypeError as ex:
            LOG.error(ex)

            #TODO(kgriffs): Improve these messages
            title = _('Invalid queue metatada')
            msg = _('The queue metadata could not be read.')
            raise falcon.HTTPInternalServerError(title, msg)

    def on_delete(self, req, resp, tenant_id, queue_name):
        self.queue_ctrl.delete(queue_name,
                               tenant=tenant_id)

        resp.status = falcon.HTTP_204


def _filtered(obj):
    #TODO(zyuan): remove this check once we have a reserved field
    if type(obj) is not dict:
        raise helpers.MalformedJSON

    return obj

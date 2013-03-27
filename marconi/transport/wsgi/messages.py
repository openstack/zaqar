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

from marconi.storage import exceptions
from marconi.transport import helpers


class CollectionResource(object):

    __slots__ = ('msg_ctrl')

    def __init__(self, message_controller):
        self.msg_ctrl = message_controller

    def on_post(self, req, resp, tenant_id, queue_name):
        uuid = req.get_header('Client-ID', required=True)

        if req.content_length is None or req.content_length == 0:
            raise falcon.HTTPBadRequest(_('Bad request'),
                                        _('Missing message contents.'))

        def filtered(ls):
            try:
                if len(ls) < 1:
                    raise helpers.MalformedJSON

                for m in ls:
                    #TODO(zyuan): verify the TTL values
                    yield {'ttl': m['ttl'], 'body': m['body']}

            except Exception:
                raise helpers.MalformedJSON

        try:
            ls = filtered(helpers.read_json(req.stream))
            ns = self.msg_ctrl.post(queue_name,
                                    messages=ls,
                                    tenant=tenant_id,
                                    client_uuid=uuid)

            resp.location = req.path + '/' + ','.join(
                [n.encode('utf-8') for n in ns])
            resp.status = falcon.HTTP_201

        except helpers.MalformedJSON:
            raise falcon.HTTPBadRequest(_('Bad request'),
                                        _('Malformed messages.'))

        except exceptions.DoesNotExist:
            raise falcon.HTTPNotFound

    def on_get(self, req, resp, tenant_id, queue_name):
        uuid = req.get_header('Client-ID', required=True)

        #TODO(zyuan): use falcon's new api to check these
        kwargs = {
            'marker': req.get_param('marker'),
            'limit': req.get_param_as_int('limit'),
            'echo': {'true': True,
                     'false': False}.get(req.get_param('echo'))
        }
        kwargs = dict([(k, v) for k, v in kwargs.items()
                       if v is not None])

        resp_dict = {}

        try:
            msgs = self.msg_ctrl.list(queue_name,
                                      tenant=tenant_id,
                                      client_uuid=uuid,
                                      **kwargs)
            resp_dict['messages'] = list(msgs)

        except exceptions.DoesNotExist:
            raise falcon.HTTPNotFound

        if len(resp_dict['messages']) != 0:
            kwargs['marker'] = resp_dict['messages'][-1]['marker']
            for m in resp_dict['messages']:
                m.pop('marker')

            resp_dict['links'] = [
                {
                    'rel': 'next',
                    'href': req.path + '?' + helpers.join_params(kwargs)
                }
            ]

            resp.content_location = req.path + '?' + req.query_string
            resp.body = helpers.to_json(resp_dict)
            resp.status = falcon.HTTP_200
        else:
            resp.status = falcon.HTTP_204


class ItemResource(object):

    __slots__ = ('msg_ctrl')

    def __init__(self, message_controller):
        self.msg_ctrl = message_controller

    def on_get(self, req, resp, tenant_id, queue_name, message_id):
        try:
            msg = self.msg_ctrl.get(queue_name,
                                    message_id=message_id,
                                    tenant=tenant_id)

            resp.content_location = req.path
            resp.body = helpers.to_json(msg)
            resp.status = falcon.HTTP_200

        except exceptions.DoesNotExist:
            raise falcon.HTTPNotFound

    def on_delete(self, req, resp, tenant_id, queue_name, message_id):
        try:
            self.msg_ctrl.delete(queue_name,
                                 message_id=message_id,
                                 tenant=tenant_id,
                                 claim=req.get_param('claim_id'))

            resp.status = falcon.HTTP_204

        except exceptions.NotPermitted:
            resp.status = falcon.HTTP_403

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

from zaqar.api.v2 import endpoints
from zaqar.api.v2 import request as schema_validator

from zaqar.common.api import request
from zaqar.common.api import response
from zaqar.common import consts
from zaqar.common import errors
from zaqar.common import urls


class Handler(object):
    """Defines API handler

    The handler validates and process the requests
    """

    _actions_mapping = {
        consts.MESSAGE_LIST: 'GET',
        consts.MESSAGE_GET: 'GET',
        consts.MESSAGE_GET_MANY: 'GET',
        consts.MESSAGE_POST: 'POST',
        consts.MESSAGE_DELETE: 'DELETE',
        consts.MESSAGE_DELETE_MANY: 'DELETE'
    }

    def __init__(self, storage, control, validate, defaults):
        self.v2_endpoints = endpoints.Endpoints(storage, control,
                                                validate, defaults)
        self._subscription_factory = None

    def set_subscription_factory(self, factory):
        self._subscription_factory = factory

    def clean_subscriptions(self, subscriptions):
        for resp in subscriptions:
            body = {'queue_name': resp._request._body.get('queue_name'),
                    'subscription_id': resp._body.get('subscription_id')}
            payload = {'body': body, 'headers': resp._request._headers}
            req = self.create_request(payload)
            self.v2_endpoints.subscription_delete(req)

    def process_request(self, req, protocol):
        # FIXME(vkmc): Control API version
        if req._action == consts.SUBSCRIPTION_CREATE:
            subscriber = req._body.get('subscriber')
            if not subscriber:
                # Default to the connected websocket as subscriber
                subscriber = self._subscription_factory.get_subscriber(
                    protocol)
            return self.v2_endpoints.subscription_create(req, subscriber)

        return getattr(self.v2_endpoints, req._action)(req)

    @staticmethod
    def validate_request(payload, req):
        """Validate a request and its payload against a schema.

        :return: a Response object if validation failed, None otherwise.
        """
        try:
            action = payload.get('action')
            validator = schema_validator.RequestSchema()
            is_valid = validator.validate(action=action, body=payload)
        except errors.InvalidAction as ex:
            body = {'error': str(ex)}
            headers = {'status': 400}
            return response.Response(req, body, headers)
        else:
            if not is_valid:
                body = {'error': 'Schema validation failed.'}
                headers = {'status': 400}
                return response.Response(req, body, headers)

    def create_response(self, code, body, req=None):
        if req is None:
            req = self.create_request()
        headers = {'status': code}
        return response.Response(req, body, headers)

    @staticmethod
    def create_request(payload=None, env=None):
        if payload is None:
            payload = {}
        action = payload.get('action')
        body = payload.get('body', {})
        headers = payload.get('headers')

        return request.Request(action=action, body=body,
                               headers=headers, api="v2", env=env)

    def get_defaults(self):
        return self.v2_endpoints._defaults

    def verify_signature(self, key, payload):
        action = payload.get('action')
        method = self._actions_mapping.get(action)

        headers = payload.get('headers', {})
        project = headers.get('X-Project-ID')
        expires = headers.get('URL-Expires')
        methods = headers.get('URL-Methods')
        paths = headers.get('URL-Paths')
        signature = headers.get('URL-Signature')

        if not method or method not in methods:
            return False

        try:
            verified = urls.verify_signed_headers_data(key, paths,
                                                       project=project,
                                                       methods=methods,
                                                       expires=expires,
                                                       signature=signature)
        except ValueError:
            return False

        return verified

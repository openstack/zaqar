# Copyright (c) 2015 Catalyst IT Ltd.
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


class ItemResource(object):

    __slots__ = ('_validate', '_subscription_controller')

    def __init__(self, validate, subscription_controller):
        self._validate = validate
        self._subscription_controller = subscription_controller

    @decorators.TransportLog("Subscription")
    @acl.enforce("subscription:get")
    def on_get(self, req, resp, project_id, queue_name, subscription_id):
        try:
            resp_dict = self._subscription_controller.get(queue_name,
                                                          subscription_id,
                                                          project=project_id)

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Subscription could not be retrieved.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.body = utils.to_json(resp_dict)
        # status defaults to 200

    @decorators.TransportLog("Subscription")
    @acl.enforce("subscription:delete")
    def on_delete(self, req, resp, project_id, queue_name, subscription_id):
        try:
            self._subscription_controller.delete(queue_name,
                                                 subscription_id,
                                                 project=project_id)

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Subscription could not be deleted.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204

    @decorators.TransportLog("Subscription")
    @acl.enforce("subscription:update")
    def on_patch(self, req, resp, project_id, queue_name, subscription_id):
        if req.content_length:
            document = wsgi_utils.deserialize(req.stream, req.content_length)
        else:
            document = {}

        try:
            self._validate.subscription_patching(document)
            self._subscription_controller.update(queue_name, subscription_id,
                                                 project=project_id,
                                                 **document)
            resp.status = falcon.HTTP_204
            resp.location = req.path
        except storage_errors.SubscriptionDoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))
        except storage_errors.SubscriptionAlreadyExists as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPConflict(six.text_type(ex))
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))
        except Exception as ex:
            LOG.exception(ex)
            description = (_(u'Subscription %(subscription_id)s could not be'
                             ' updated.') %
                           dict(subscription_id=subscription_id))
            raise falcon.HTTPBadRequest(_('Unable to update subscription'),
                                        description)


class CollectionResource(object):

    __slots__ = ('_subscription_controller', '_validate',
                 '_default_subscription_ttl')

    def __init__(self, validate, subscription_controller,
                 default_subscription_ttl):
        self._subscription_controller = subscription_controller
        self._validate = validate
        self._default_subscription_ttl = default_subscription_ttl

    @decorators.TransportLog("Subscription collection")
    @acl.enforce("subscription:get_all")
    def on_get(self, req, resp, project_id, queue_name):
        kwargs = {}

        # NOTE(kgriffs): This syntax ensures that
        # we don't clobber default values with None.
        req.get_param('marker', store=kwargs)
        req.get_param_as_int('limit', store=kwargs)

        try:
            self._validate.subscription_listing(**kwargs)
            results = self._subscription_controller.list(queue_name,
                                                         project=project_id,
                                                         **kwargs)
            # Buffer list of subscriptions. Can raise NoPoolFound error.
            subscriptions = list(next(results))
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Subscriptions could not be listed.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Got some. Prepare the response.
        kwargs['marker'] = next(results) or kwargs.get('marker', '')

        links = []
        if subscriptions:
            links = [
                {
                    'rel': 'next',
                    'href': req.path + falcon.to_query_str(kwargs)
                }
            ]
        response_body = {
            'subscriptions': subscriptions,
            'links': links
        }

        resp.body = utils.to_json(response_body)
        # status defaults to 200

    @decorators.TransportLog("Subscription item")
    @acl.enforce("subscription:create")
    def on_post(self, req, resp, project_id, queue_name):
        if req.content_length:
            document = wsgi_utils.deserialize(req.stream, req.content_length)
        else:
            document = {}

        try:
            self._validate.subscription_posting(document)
            subscriber = document['subscriber']
            ttl = document.get('ttl', self._default_subscription_ttl)
            options = document.get('options', {})
            created = self._subscription_controller.create(queue_name,
                                                           subscriber,
                                                           ttl,
                                                           options,
                                                           project=project_id)

        except storage_errors.QueueDoesNotExist as ex:
            LOG.exception(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))
        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Subscription could not be created.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        if created:
            resp.location = req.path
            resp.status = falcon.HTTP_201
            resp.body = utils.to_json(
                {'subscription_id': six.text_type(created)})
        else:
            description = _(u'Such subscription already exists. Subscriptions '
                            u'are unique by project + queue + subscriber URI.')
            raise wsgi_errors.HTTPConflict(description, headers={'location':
                                                                 req.path})

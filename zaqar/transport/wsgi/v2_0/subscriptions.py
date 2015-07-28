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

from zaqar.i18n import _
from zaqar.storage import errors as storage_errors
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

    def on_get(self, req, resp, project_id, queue_name, subscription_id):
        LOG.debug(u'Subscription GET - subscription id: %(subscription_id)s,'
                  u' project: %(project)s, queue: %(queue)s',
                  {'subscription_id': subscription_id, 'project': project_id,
                   'queue': queue_name})
        try:
            resp_dict = self._subscription_controller.get(queue_name,
                                                          subscription_id,
                                                          project=project_id)

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Subscription could not be retrieved.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.body = utils.to_json(resp_dict)
        # status defaults to 200

    def on_delete(self, req, resp, project_id, queue_name, subscription_id):
        LOG.debug(u'Subscription DELETE - '
                  u'subscription id: %(subscription_id)s,'
                  u' project: %(project)s, queue: %(queue)s',
                  {'subscription_id': subscription_id, 'project': project_id,
                   'queue': queue_name})
        try:
            self._subscription_controller.delete(queue_name,
                                                 subscription_id,
                                                 project=project_id)

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Subscription could not be deleted.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        resp.status = falcon.HTTP_204

    def on_patch(self, req, resp, project_id, queue_name, subscription_id):
        LOG.debug(u'Subscription PATCH - subscription id: %(subscription_id)s,'
                  u' project: %(project)s, queue: %(queue)s',
                  {'subscription_id': subscription_id, 'project': project_id,
                   'queue': queue_name})

        if req.content_length:
            document = wsgi_utils.deserialize(req.stream, req.content_length)

        try:
            self._validate.subscription_patching(document)
            self._subscription_controller.update(queue_name, subscription_id,
                                                 project=project_id,
                                                 **document)
            resp.status = falcon.HTTP_204
            resp.location = req.path
        except storage_errors.SubscriptionDoesNotExist as ex:
            LOG.debug(ex)
            raise falcon.HTTPNotFound()
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))
        except Exception as ex:
            LOG.exception(ex)
            description = (_(u'Subscription {subscription_id} could not be'
                             ' updated.') %
                           dict(subscription_id=subscription_id))
            raise falcon.HTTPBadRequest(_('Unable to update subscription'),
                                        description)


class CollectionResource(object):

    __slots__ = ('_subscription_controller', '_validate')

    def __init__(self, validate, subscription_controller):
        self._subscription_controller = subscription_controller
        self._validate = validate

    def on_get(self, req, resp, project_id, queue_name):
        LOG.debug(u'Subscription collection GET - project: %(project)s, '
                  u'queue: %(queue)s',
                  {'project': project_id, 'queue': queue_name})

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
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Subscriptions could not be listed.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        # Buffer list of subscriptions
        subscriptions = list(next(results))

        # Got some. Prepare the response.
        kwargs['marker'] = next(results) or kwargs.get('marker', '')

        response_body = {
            'subscriptions': subscriptions,
            'links': [
                {
                    'rel': 'next',
                    'href': req.path + falcon.to_query_str(kwargs)
                }
            ]
        }

        resp.body = utils.to_json(response_body)
        # status defaults to 200

    def on_post(self, req, resp, project_id, queue_name):
        LOG.debug(u'Subscription item POST - project: %(project)s, '
                  u'queue: %(queue)s',
                  {'project': project_id, 'queue': queue_name})

        if req.content_length:
            document = wsgi_utils.deserialize(req.stream, req.content_length)

        try:
            self._validate.subscription_posting(document)
            subscriber = document['subscriber']
            ttl = int(document['ttl'])
            options = document['options']
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

        resp.status = falcon.HTTP_201 if created else falcon.HTTP_409
        resp.location = req.path
        if created:
            resp.body = utils.to_json(
                {'subscription_id': six.text_type(created)})

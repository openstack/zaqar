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
import datetime

import falcon
from oslo_log import log as logging
from oslo_utils import netutils
from oslo_utils import timeutils
import six
from stevedore import driver

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar.notification import notifier
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

    @decorators.TransportLog("Subscriptions item")
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

    @decorators.TransportLog("Subscriptions item")
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

    @decorators.TransportLog("Subscriptions item")
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
                 '_default_subscription_ttl', '_queue_controller',
                 '_conf', '_notification')

    def __init__(self, validate, subscription_controller,
                 default_subscription_ttl, queue_controller, conf):
        self._subscription_controller = subscription_controller
        self._validate = validate
        self._default_subscription_ttl = default_subscription_ttl
        self._queue_controller = queue_controller
        self._conf = conf
        self._notification = notifier.NotifierDriver()

    @decorators.TransportLog("Subscriptions collection")
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

    @decorators.TransportLog("Subscriptions collection")
    @acl.enforce("subscription:create")
    def on_post(self, req, resp, project_id, queue_name):
        if req.content_length:
            document = wsgi_utils.deserialize(req.stream, req.content_length)
        else:
            document = {}

        try:
            if not self._queue_controller.exists(queue_name, project_id):
                self._queue_controller.create(queue_name, project=project_id)
            self._validate.subscription_posting(document)
            subscriber = document['subscriber']
            options = document.get('options', {})
            url = netutils.urlsplit(subscriber)
            ttl = document.get('ttl', self._default_subscription_ttl)
            mgr = driver.DriverManager('zaqar.notification.tasks', url.scheme,
                                       invoke_on_load=True)
            req_data = req.headers.copy()
            req_data.update(req.env)
            mgr.driver.register(subscriber, options, ttl, project_id, req_data)

            created = self._subscription_controller.create(queue_name,
                                                           subscriber,
                                                           ttl,
                                                           options,
                                                           project=project_id)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))
        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Subscription could not be created.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

        now = timeutils.utcnow_ts()
        now_dt = datetime.datetime.utcfromtimestamp(now)
        expires = now_dt + datetime.timedelta(seconds=ttl)
        api_version = req.path.split('/')[1]
        if created:
            subscription = self._subscription_controller.get(queue_name,
                                                             created,
                                                             project_id)
            # send confirm notification
            self._notification.send_confirm_notification(
                queue_name, subscription, self._conf, project_id,
                str(expires), api_version)

            resp.location = req.path
            resp.status = falcon.HTTP_201
            resp.body = utils.to_json(
                {'subscription_id': six.text_type(created)})
        else:
            subscription = self._subscription_controller.get_with_subscriber(
                queue_name, subscriber, project_id)
            confirmed = subscription.get('confirmed', True)
            if confirmed:
                description = _(u'Such subscription already exists.'
                                u'Subscriptions are unique by project + queue '
                                u'+ subscriber URI.')
                raise wsgi_errors.HTTPConflict(description,
                                               headers={'location': req.path})
            else:
                # The subscription is not confirmed, re-send confirm
                # notification
                self._notification.send_confirm_notification(
                    queue_name, subscription, self._conf, project_id,
                    str(expires), api_version)

                resp.location = req.path
                resp.status = falcon.HTTP_201
                resp.body = utils.to_json(
                    {'subscription_id': six.text_type(subscription['id'])})


class ConfirmResource(object):

    __slots__ = ('_subscription_controller', '_validate', '_notification',
                 '_conf')

    def __init__(self, validate, subscription_controller, conf):
        self._subscription_controller = subscription_controller
        self._validate = validate
        self._notification = notifier.NotifierDriver()
        self._conf = conf

    @decorators.TransportLog("Subscriptions confirmation item")
    @acl.enforce("subscription:confirm")
    def on_put(self, req, resp, project_id, queue_name, subscription_id):
        if req.content_length:
            document = wsgi_utils.deserialize(req.stream, req.content_length)
        else:
            document = {}

        try:
            self._validate.subscription_confirming(document)
            confirmed = document.get('confirmed')
            self._subscription_controller.confirm(queue_name, subscription_id,
                                                  project=project_id,
                                                  confirmed=confirmed)
            if confirmed is False:
                now = timeutils.utcnow_ts()
                now_dt = datetime.datetime.utcfromtimestamp(now)
                ttl = self._conf.transport.default_subscription_ttl
                expires = now_dt + datetime.timedelta(seconds=ttl)
                api_version = req.path.split('/')[1]
                sub = self._subscription_controller.get(queue_name,
                                                        subscription_id,
                                                        project=project_id)
                self._notification.send_confirm_notification(queue_name,
                                                             sub,
                                                             self._conf,
                                                             project_id,
                                                             str(expires),
                                                             api_version,
                                                             True)
            resp.status = falcon.HTTP_204
            resp.location = req.path
        except storage_errors.SubscriptionDoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))
        except Exception as ex:
            LOG.exception(ex)
            description = (_(u'Subscription %(subscription_id)s could not be'
                             ' confirmed.') %
                           dict(subscription_id=subscription_id))
            raise falcon.HTTPBadRequest(_('Unable to confirm subscription'),
                                        description)

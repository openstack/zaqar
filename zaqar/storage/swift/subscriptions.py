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

import functools

from oslo_serialization import jsonutils
from oslo_utils import uuidutils
import swiftclient
import urllib

from zaqar import storage
from zaqar.storage import errors
from zaqar.storage.swift import utils


class SubscriptionController(storage.Subscription):
    """Implements subscription resource operations with swift backend.

    Subscriptions are scoped by queue and project.

    subscription -> Swift mapping:
       +----------------+---------------------------------------+
       | Attribute      | Storage location                      |
       +----------------+---------------------------------------+
       | Sub UUID       | Object name                           |
       +----------------+---------------------------------------+
       | Queue Name     | Container name prefix                 |
       +----------------+---------------------------------------+
       | Project name   | Container name prefix                 |
       +----------------+---------------------------------------+
       | Created time   | Object Creation Time                  |
       +----------------+---------------------------------------+
       | Sub options    | Object content                        |
       +----------------+---------------------------------------+
    """

    def __init__(self, *args, **kwargs):
        super(SubscriptionController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection

    def list(self, queue, project=None, marker=None,
             limit=storage.DEFAULT_SUBSCRIPTIONS_PER_PAGE):
        container = utils._subscription_container(queue, project)
        try:
            _, objects = self._client.get_container(container,
                                                    limit=limit,
                                                    marker=marker)
        except swiftclient.ClientException as exc:
            if exc.http_status == 404:
                objects = []
            else:
                raise
        marker_next = {}
        yield utils.SubscriptionListCursor(
            objects, marker_next,
            functools.partial(self._client.get_object, container))
        yield marker_next and marker_next['next']

    def get(self, queue, subscription_id, project=None):
        container = utils._subscription_container(queue, project)
        try:
            headers, data = self._client.get_object(container, subscription_id)
        except swiftclient.ClientException as exc:
            if exc.http_status == 404:
                raise errors.SubscriptionDoesNotExist(subscription_id)
            raise
        return utils._subscription_to_json(data, headers)

    def create(self, queue, subscriber, ttl, options, project=None):
        sub_container = utils._subscriber_container(queue, project)
        slug = uuidutils.generate_uuid()
        try:
            utils._put_or_create_container(
                self._client,
                sub_container,
                urllib.quote_plus(subscriber),
                contents=slug,
                headers={'x-delete-after': ttl, 'if-none-match': '*'})
        except swiftclient.ClientException as exc:
            if exc.http_status == 412:
                return
            raise
        container = utils._subscription_container(queue, project)
        data = {'id': slug,
                'source': queue,
                'subscriber': subscriber,
                'options': options,
                'ttl': ttl,
                'confirmed': False}
        utils._put_or_create_container(
            self._client, container, slug, contents=jsonutils.dumps(data),
            content_type='application/json', headers={'x-delete-after': ttl})
        return slug

    def update(self, queue, subscription_id, project=None, **kwargs):
        container = utils._subscription_container(queue, project)
        data = self.get(queue, subscription_id, project)
        data.pop('age')
        ttl = data['ttl']
        if 'subscriber' in kwargs:
            sub_container = utils._subscriber_container(queue, project)
            try:
                self._client.put_object(
                    sub_container,
                    urllib.quote_plus(kwargs['subscriber']),
                    contents=subscription_id,
                    headers={'x-delete-after': ttl, 'if-none-match': '*'})
            except swiftclient.ClientException as exc:
                if exc.http_status == 412:
                    raise errors.SubscriptionAlreadyExists()
                raise
            self._client.delete_object(sub_container,
                                       urllib.quote_plus(data['subscriber']))
        data.update(kwargs)
        self._client.put_object(container,
                                subscription_id,
                                contents=jsonutils.dumps(data),
                                content_type='application/json',
                                headers={'x-delete-after': ttl})

    def exists(self, queue, subscription_id, project=None):
        container = utils._subscription_container(queue, project)
        return self._client.head_object(container, subscription_id)

    def delete(self, queue, subscription_id, project=None):
        try:
            data = self.get(queue, subscription_id, project)
        except errors.SubscriptionDoesNotExist:
            return
        sub_container = utils._subscriber_container(queue, project)
        try:
            self._client.delete_object(sub_container,
                                       urllib.quote_plus(data['subscriber']))
        except swiftclient.ClientException as exc:
            if exc.http_status != 404:
                raise
        container = utils._subscription_container(queue, project)
        try:
            self._client.delete_object(container, subscription_id)
        except swiftclient.ClientException as exc:
            if exc.http_status != 404:
                raise

    def get_with_subscriber(self, queue, subscriber, project=None):
        sub_container = utils._subscriber_container(queue, project)
        headers, obj = self._client.get_object(sub_container,
                                               urllib.quote_plus(subscriber))
        return self.get(queue, obj, project)

    def confirm(self, queue, subscription_id, project=None, confirmed=True):
        self.update(queue, subscription_id, project, confirmed=confirmed)

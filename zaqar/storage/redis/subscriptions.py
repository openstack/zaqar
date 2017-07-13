# Copyright (c) 2015 Catalyst IT Ltd.
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

import functools

import msgpack
from oslo_utils import timeutils
from oslo_utils import uuidutils
import redis

from zaqar.common import utils as common_utils
from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.redis import models
from zaqar.storage.redis import utils


SubscriptionEnvelope = models.SubscriptionEnvelope

SUBSET_INDEX_KEY = 'subset_index'
SUBSCRIPTION_IDS_SUFFIX = 'subscriptions'


class SubscriptionController(base.Subscription):
    """Implements subscription resource operations using MongoDB.

    Subscriptions are unique by project + queue/topic + subscriber.

    Schema:
      's': source :: six.text_type
      'u': subscriber:: six.text_type
      't': ttl:: int
      'e': expires: int
      'o': options :: dict
      'p': project :: six.text_type
    """
    def __init__(self, *args, **kwargs):
        super(SubscriptionController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection
        self._packer = msgpack.Packer(encoding='utf-8',
                                      use_bin_type=True).pack
        self._unpacker = functools.partial(msgpack.unpackb, encoding='utf-8')

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def list(self, queue, project=None, marker=None, limit=10):
        client = self._client
        subset_key = utils.scope_subscription_ids_set(queue,
                                                      project,
                                                      SUBSCRIPTION_IDS_SUFFIX)
        rank = client.zrank(subset_key, marker)
        start = rank + 1 if rank is not None else 0

        cursor = (q for q in client.zrange(subset_key, start,
                                           start + limit - 1))
        marker_next = {}

        def denormalizer(record, sid):
            now = timeutils.utcnow_ts()
            ttl = int(record[2])
            expires = int(record[3])
            created = expires - ttl
            is_confirmed = True
            if len(record) == 6:
                is_confirmed = record[5] == str(True)
            ret = {
                'id': sid,
                'source': record[0],
                'subscriber': record[1],
                'ttl': ttl,
                'age': now - created,
                'options': self._unpacker(record[4]),
                'confirmed': is_confirmed,
            }
            marker_next['next'] = sid

            return ret

        yield utils.SubscriptionListCursor(self._client, cursor, denormalizer)
        yield marker_next and marker_next['next']

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def get(self, queue, subscription_id, project=None):
        subscription = None
        if self.exists(queue, subscription_id, project):
            subscription = SubscriptionEnvelope.from_redis(subscription_id,
                                                           self._client)
        if subscription:
            now = timeutils.utcnow_ts()
            return subscription.to_basic(now)
        else:
            raise errors.SubscriptionDoesNotExist(subscription_id)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def create(self, queue, subscriber, ttl, options, project=None):
        subscription_id = uuidutils.generate_uuid()
        subset_key = utils.scope_subscription_ids_set(queue,
                                                      project,
                                                      SUBSCRIPTION_IDS_SUFFIX)

        source = queue
        now = timeutils.utcnow_ts()
        expires = now + ttl
        confirmed = False

        subscription = {'id': subscription_id,
                        's': source,
                        'u': subscriber,
                        't': ttl,
                        'e': expires,
                        'o': self._packer(options),
                        'p': project,
                        'c': confirmed}

        try:
            # Pipeline ensures atomic inserts.
            with self._client.pipeline() as pipe:
                if not self._is_duplicated_subscriber(subscriber,
                                                      queue,
                                                      project):
                    pipe.zadd(subset_key, 1,
                              subscription_id).hmset(subscription_id,
                                                     subscription)
                    pipe.expire(subscription_id, ttl)
                    pipe.execute()
                else:
                    return None
            return subscription_id
        except redis.exceptions.ResponseError:
            return None

    def _is_duplicated_subscriber(self, subscriber, queue, project):
        """Check if the subscriber is existing or not.

        Given the limitation of Redis' expires(), it's hard to auto expire
        subscriber from the set and subscription id from the sorted set, so
        this method is used to do a ugly duplication check when adding a new
        subscription so that we don't need the set for subscriber. And as a
        side effect, this method will remove the unreachable subscription's id
        from the sorted set.
        """
        subset_key = utils.scope_subscription_ids_set(queue,
                                                      project,
                                                      SUBSCRIPTION_IDS_SUFFIX)
        try:
            sub_ids = (q for q in self._client.zrange(subset_key, 0, -1))
            for s_id in sub_ids:
                subscription = self._client.hmget(s_id,
                                                  ['s', 'u', 't', 'o', 'c'])
                if subscription == [None, None, None, None, None]:
                    # NOTE(flwang): Under this check, that means the
                    # subscription has been expired. So redis can't get
                    # the subscription but the id is still there. So let's
                    # delete the id for clean up.
                    self._client.zrem(subset_key, s_id)
                if subscription[1] == subscriber:
                    return True
            return False
        except redis.exceptions.ResponseError:
            return True

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def exists(self, queue, subscription_id, project=None):
        subset_key = utils.scope_subscription_ids_set(queue, project,
                                                      SUBSCRIPTION_IDS_SUFFIX)

        return self._client.zrank(subset_key, subscription_id) is not None

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def update(self, queue, subscription_id, project=None, **kwargs):
        names = ('subscriber', 'ttl', 'options')
        key_transform = lambda x: 'u' if x == 'subscriber' else x[0]
        fields = common_utils.fields(kwargs, names,
                                     pred=lambda x: x is not None,
                                     key_transform=key_transform)
        assert fields, ('`subscriber`, `ttl`, '
                        'or `options` not found in kwargs')

        # Let's get our subscription by ID. If it does not exist,
        # SubscriptionDoesNotExist error will be raised internally.
        subscription_to_update = self.get(queue, subscription_id,
                                          project=project)

        new_subscriber = fields.get('u')

        # Let's do some checks to prevent subscription duplication.
        if new_subscriber:
            # Check if 'new_subscriber' is really new for our subscription.
            if subscription_to_update['subscriber'] != new_subscriber:
                # It's new. We should raise error if this subscriber already
                # exists for the queue and project.
                if self._is_duplicated_subscriber(new_subscriber, queue,
                                                  project):
                    raise errors.SubscriptionAlreadyExists()

        # NOTE(Eva-i): if there are new options, we need to pack them before
        # sending to the database.
        new_options = fields.get('o')
        if new_options is not None:
            fields['o'] = self._packer(new_options)

        new_ttl = fields.get('t')
        if new_ttl is not None:
            now = timeutils.utcnow_ts()
            expires = now + new_ttl
            fields['e'] = expires

        # Pipeline ensures atomic inserts.
        with self._client.pipeline() as pipe:
            pipe.hmset(subscription_id, fields)
            if new_ttl is not None:
                pipe.expire(subscription_id, new_ttl)
            pipe.execute()

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def delete(self, queue, subscription_id, project=None):
        subset_key = utils.scope_subscription_ids_set(queue, project,
                                                      SUBSCRIPTION_IDS_SUFFIX)

        if self._client.zrank(subset_key, subscription_id) is not None:
            # NOTE(prashanthr_): Pipelining is used to mitigate race conditions
            with self._client.pipeline() as pipe:
                pipe.zrem(subset_key, subscription_id)
                pipe.delete(subscription_id)
                pipe.execute()

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def get_with_subscriber(self, queue, subscriber, project=None):
        subset_key = utils.scope_subscription_ids_set(queue,
                                                      project,
                                                      SUBSCRIPTION_IDS_SUFFIX)
        sub_ids = (q for q in self._client.zrange(subset_key, 0, -1))
        for s_id in sub_ids:
            subscription = self._client.hmget(s_id,
                                              ['s', 'u', 't', 'o', 'c'])
            if subscription[1] == subscriber:
                subscription = SubscriptionEnvelope.from_redis(s_id,
                                                               self._client)
                now = timeutils.utcnow_ts()
                return subscription.to_basic(now)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def confirm(self, queue, subscription_id, project=None, confirmed=True):
        # Let's get our subscription by ID. If it does not exist,
        # SubscriptionDoesNotExist error will be raised internally.
        self.get(queue, subscription_id, project=project)

        fields = {'c': confirmed}
        with self._client.pipeline() as pipe:
            pipe.hmset(subscription_id, fields)
            pipe.execute()

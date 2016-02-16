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
import uuid

import msgpack
from oslo_utils import timeutils
import redis

from zaqar.common import decorators
from zaqar.common import utils as common_utils
from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.redis import models
from zaqar.storage.redis import utils


SubscriptionEnvelope = models.SubscriptionEnvelope

SUBSET_INDEX_KEY = 'subset_index'
SUBSCRIPTION_IDS_SUFFIX = 'subscriptions'
SUBSCRIBERS_SUFFIX = 'subscribers'


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

    @decorators.lazy_property(write=False)
    def _queue_ctrl(self):
        return self.driver.queue_controller

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def list(self, queue, project=None, marker=None, limit=10):
        client = self._client
        subset_key = utils.scope_subscription_ids_set(queue,
                                                      project,
                                                      SUBSCRIPTION_IDS_SUFFIX)
        rank = client.zrank(subset_key, marker)
        start = rank + 1 if rank else 0

        cursor = (q for q in client.zrange(subset_key, start,
                                           start + limit - 1))
        marker_next = {}

        def denormalizer(record, sid):
            ret = {
                'id': sid,
                'source': record[0],
                'subscriber': record[1],
                'ttl': int(record[2]),
                'options': self._unpacker(record[3]),
            }
            marker_next['next'] = sid

            return ret

        yield utils.SubscriptionListCursor(self._client, cursor, denormalizer)
        yield marker_next and marker_next['next']

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def get(self, queue, subscription_id, project=None):

        subscription = SubscriptionEnvelope.from_redis(subscription_id,
                                                       self._client)
        now = timeutils.utcnow_ts()

        if subscription and not utils.subscription_expired_filter(subscription,
                                                                  now):
            return subscription.to_basic(now)
        else:
            raise errors.SubscriptionDoesNotExist(subscription_id)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def create(self, queue, subscriber, ttl, options, project=None):
        member_key = utils.scope_subscribers_set(queue, project,
                                                 SUBSCRIBERS_SUFFIX)
        if self._client.sismember(member_key, subscriber):
            return None
        subscription_id = str(uuid.uuid4())
        subset_key = utils.scope_subscription_ids_set(queue,
                                                      project,
                                                      SUBSCRIPTION_IDS_SUFFIX)

        source = queue
        now = timeutils.utcnow_ts()
        ttl = int(ttl)
        expires = now + ttl

        subscription = {'id': subscription_id,
                        's': source,
                        'u': subscriber,
                        't': ttl,
                        'e': expires,
                        'o': self._packer(options),
                        'p': project}

        if not self._queue_ctrl.exists(queue, project):
            raise errors.QueueDoesNotExist(queue, project)
        try:
            # Pipeline ensures atomic inserts.
            with self._client.pipeline() as pipe:
                pipe.sadd(member_key, subscriber)
                pipe.zadd(subset_key, 1,
                          subscription_id).hmset(subscription_id, subscription)
                pipe.execute()
            return subscription_id
        except redis.exceptions.ResponseError:
            return None

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

        # Pipeline ensures atomic inserts.
        with self._client.pipeline() as pipe:
            pipe.hmset(subscription_id, fields)
            pipe.execute()

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def delete(self, queue, subscription_id, project=None):
        subset_key = utils.scope_subscription_ids_set(queue, project,
                                                      SUBSCRIPTION_IDS_SUFFIX)
        member_key = utils.scope_subscribers_set(queue, project,
                                                 SUBSCRIBERS_SUFFIX)
        subscriber = self._client.hget(subscription_id, 'u')
        # NOTE(prashanthr_): Pipelining is used to mitigate race conditions
        with self._client.pipeline() as pipe:
            pipe.srem(member_key, subscriber)
            pipe.zrem(subset_key, subscription_id)
            pipe.delete(subscription_id)
            pipe.execute()

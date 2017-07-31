# Copyright (c) 2014 Catalyst IT Ltd.
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
import datetime

from oslo_utils import timeutils
import pymongo.errors

from zaqar.common import utils as common_utils
from zaqar import storage
from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.mongodb import utils

ID_INDEX_FIELDS = [('_id', 1)]

SUBSCRIPTIONS_INDEX = [
    ('s', 1),
    ('u', 1),
    ('p', 1),
]

# For removing expired subscriptions
TTL_INDEX_FIELDS = [
    ('e', 1),
]


class SubscriptionController(base.Subscription):
    """Implements subscription resource operations using MongoDB.

    Subscriptions are unique by project + queue/topic + subscriber.

    Schema:
      's': source :: six.text_type
      'u': subscriber:: six.text_type
      't': ttl:: int
      'e': expires: datetime.datetime
      'o': options :: dict
      'p': project :: six.text_type
      'c': confirmed :: boolean
    """

    def __init__(self, *args, **kwargs):
        super(SubscriptionController, self).__init__(*args, **kwargs)
        self._collection = self.driver.subscriptions_database.subscriptions
        self._collection.ensure_index(SUBSCRIPTIONS_INDEX, unique=True)
        # NOTE(flwang): MongoDB will automatically delete the subscription
        # from the subscriptions collection when the subscription's 'e' value
        # is older than the number of seconds specified in expireAfterSeconds,
        # i.e. 0 seconds older in this case. As such, the data expires at the
        # specified 'e' value.
        self._collection.ensure_index(TTL_INDEX_FIELDS, name='ttl',
                                      expireAfterSeconds=0,
                                      background=True)

    @utils.raises_conn_error
    def list(self, queue, project=None, marker=None,
             limit=storage.DEFAULT_SUBSCRIPTIONS_PER_PAGE):
        query = {'s': queue, 'p': project}
        if marker is not None:
            query['_id'] = {'$gt': utils.to_oid(marker)}

        projection = {'s': 1, 'u': 1, 't': 1, 'p': 1, 'o': 1, '_id': 1, 'c': 1}

        cursor = self._collection.find(query, projection=projection)
        cursor = cursor.limit(limit).sort('_id')
        marker_name = {}

        now = timeutils.utcnow_ts()

        def normalizer(record):
            marker_name['next'] = record['_id']

            return _basic_subscription(record, now)

        yield utils.HookedCursor(cursor, normalizer)
        yield marker_name and marker_name['next']

    @utils.raises_conn_error
    def get(self, queue, subscription_id, project=None):
        res = self._collection.find_one({'_id': utils.to_oid(subscription_id),
                                         'p': project,
                                         's': queue})

        if not res:
            raise errors.SubscriptionDoesNotExist(subscription_id)

        now = timeutils.utcnow_ts()
        return _basic_subscription(res, now)

    @utils.raises_conn_error
    def create(self, queue, subscriber, ttl, options, project=None):
        source = queue
        now = timeutils.utcnow_ts()
        now_dt = datetime.datetime.utcfromtimestamp(now)
        expires = now_dt + datetime.timedelta(seconds=ttl)
        confirmed = False

        try:
            subscription_id = self._collection.insert({'s': source,
                                                       'u': subscriber,
                                                       't': ttl,
                                                       'e': expires,
                                                       'o': options,
                                                       'p': project,
                                                       'c': confirmed})
            return subscription_id
        except pymongo.errors.DuplicateKeyError:
            return None

    @utils.raises_conn_error
    def exists(self, queue, subscription_id, project=None):
        return self._collection.find_one({'_id': utils.to_oid(subscription_id),
                                          'p': project}) is not None

    @utils.raises_conn_error
    def update(self, queue, subscription_id, project=None, **kwargs):
        names = ('subscriber', 'ttl', 'options')
        key_transform = lambda x: 'u' if x == 'subscriber' else x[0]
        fields = common_utils.fields(kwargs, names,
                                     pred=lambda x: x is not None,
                                     key_transform=key_transform)
        assert fields, ('`subscriber`, `ttl`, '
                        'or `options` not found in kwargs')

        new_ttl = fields.get('t')
        if new_ttl is not None:
            now = timeutils.utcnow_ts()
            now_dt = datetime.datetime.utcfromtimestamp(now)
            expires = now_dt + datetime.timedelta(seconds=new_ttl)
            fields['e'] = expires

        try:
            res = self._collection.update_one(
                {'_id': utils.to_oid(subscription_id),
                 'p': project,
                 's': queue},
                {'$set': fields},
                upsert=False)
        except pymongo.errors.DuplicateKeyError:
            raise errors.SubscriptionAlreadyExists()
        if res.matched_count == 0:
            raise errors.SubscriptionDoesNotExist(subscription_id)

    @utils.raises_conn_error
    def delete(self, queue, subscription_id, project=None):
        self._collection.delete_one({'_id': utils.to_oid(subscription_id),
                                     'p': project,
                                     's': queue})

    @utils.raises_conn_error
    def get_with_subscriber(self, queue, subscriber, project=None):
        res = self._collection.find_one({'u': subscriber,
                                         'p': project})
        now = timeutils.utcnow_ts()
        return _basic_subscription(res, now)

    @utils.raises_conn_error
    def confirm(self, queue, subscription_id, project=None, confirmed=True):

        res = self._collection.update_one(
            {'_id': utils.to_oid(subscription_id),
             'p': project},
            {'$set': {'c': confirmed}},
            upsert=False)
        if res.matched_count == 0:
            raise errors.SubscriptionDoesNotExist(subscription_id)


def _basic_subscription(record, now):
    # NOTE(Eva-i): unused here record's field 'e' (expires) has changed it's
    # format from int (timestamp) to datetime since patch
    # 1d122b1671792aff0055ed5396111cd441fb8269. Any future change about
    # starting using 'e' field should make sure support both of the formats.
    oid = record['_id']
    age = now - utils.oid_ts(oid)
    confirmed = record.get('c', True)
    return {
        'id': str(oid),
        'source': record['s'],
        'subscriber': record['u'],
        'ttl': record['t'],
        'age': int(age),
        'options': record['o'],
        'confirmed': confirmed,
    }

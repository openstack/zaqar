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
        self._collection = self.driver.subscriptions_database.subscriptions
        queue_col = self.driver.control_driver.queues_database.queues
        self._queue_collection = queue_col
        self._collection.ensure_index(SUBSCRIPTIONS_INDEX, unique=True)

    @utils.raises_conn_error
    def list(self, queue, project=None, marker=None,
             limit=storage.DEFAULT_SUBSCRIPTIONS_PER_PAGE):
        query = {'s': queue, 'p': project}
        if marker is not None:
            query['_id'] = {'$gt': utils.to_oid(marker)}

        fields = {'s': 1, 'u': 1, 't': 1, 'p': 1, 'o': 1, '_id': 1}

        cursor = self._collection.find(query, fields=fields)
        cursor = cursor.limit(limit).sort('_id')
        marker_name = {}

        def normalizer(record):
            ret = {
                'id': str(record['_id']),
                'source': record['s'],
                'subscriber': record['u'],
                'ttl': record['t'],
                'options': record['o'],
            }
            marker_name['next'] = record['_id']

            return ret

        yield utils.HookedCursor(cursor, normalizer)
        yield marker_name and marker_name['next']

    @utils.raises_conn_error
    def get(self, queue, subscription_id, project=None):
        res = self._collection.find_one({'_id': utils.to_oid(subscription_id),
                                         'p': project})

        if not res:
            raise errors.SubscriptionDoesNotExist(subscription_id)

        return _normalize(res)

    @utils.raises_conn_error
    def create(self, queue, subscriber, ttl, options, project=None):
        source = queue
        now = timeutils.utcnow_ts()
        ttl = int(ttl)
        expires = now + ttl
        source_query = {'p_q': utils.scope_queue_name(source, project)}
        target_source = self._queue_collection.find_one(source_query,
                                                        fields={'m': 1,
                                                                '_id': 0})
        if target_source is None:
            raise errors.QueueDoesNotExist(target_source, project)
        try:
            subscription_id = self._collection.insert({'s': source,
                                                       'u': subscriber,
                                                       't': ttl,
                                                       'e': expires,
                                                       'o': options,
                                                       'p': project})
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

        res = self._collection.update({'_id': utils.to_oid(subscription_id),
                                       'p': project},
                                      {'$set': fields},
                                      upsert=False)

        if not res['updatedExisting']:
            raise errors.SubscriptionDoesNotExist(subscription_id)

    @utils.raises_conn_error
    def delete(self, queue, subscription_id, project=None):
        self._collection.remove({'_id': utils.to_oid(subscription_id),
                                 'p': project}, w=0)


def _normalize(record):
    ret = {
        'id': str(record['_id']),
        'source': record['s'],
        'subscriber': record['u'],
        'ttl': record['t'],
        'options': record['o']
    }

    return ret

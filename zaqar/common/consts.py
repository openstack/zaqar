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


TRANSPORT_DRIVERS = (
    TRANSPORT_WSGI, TRANSPORT_WEBSOCKET,
) = (
    'wsgi', 'websocket',
)

MESSAGE_STORE = (
    MSG_STORE_MONGODB,
) = (
    'mongodb',
)

MANAGEMENT_STORE = (
    MGMT_STORE_MONGODB,
) = (
    'mongodb',
)

SUBSCRIPTION_OPS = (
    SUBSCRIPTION_CREATE,
    SUBSCRIPTION_LIST,
    SUBSCRIPTION_GET,
    SUBSCRIPTION_DELETE,
) = (
    'subscription_create',
    'subscription_list',
    'subscription_get',
    'subscription_delete',
)

MESSAGE_OPS = (
    MESSAGE_POST,
    MESSAGE_LIST,
    MESSAGE_GET,
    MESSAGE_GET_MANY,
    MESSAGE_DELETE,
    MESSAGE_DELETE_MANY,
) = (
    'message_post',
    'message_list',
    'message_get',
    'message_get_many',
    'message_delete',
    'message_delete_many',
)

QUEUE_OPS = (
    QUEUE_CREATE,
    QUEUE_LIST,
    QUEUE_GET,
    QUEUE_DELETE,
    QUEUE_GET_STATS,
    QUEUE_PURGE
) = (
    'queue_create',
    'queue_list',
    'queue_get',
    'queue_delete',
    'queue_get_stats',
    'queue_purge'
)

CLAIM_OPS = (
    CLAIM_CREATE,
    CLAIM_GET,
    CLAIM_UPDATE,
    CLAIM_DELETE,
) = (
    'claim_create',
    'claim_get',
    'claim_update',
    'claim_delete',
)

POOL_OPS = (
    POOL_CREATE,
    POOL_LIST,
    POOL_GET,
    POOL_GET_DETAIL,
    POOL_UPDATE,
    POOL_DELETE,
) = (
    'pool_create',
    'pool_list',
    'pool_get',
    'pool_get_detail',
    'pool_update',
    'pool_delete',
)

FLAVOR_OPS = (
    FLAVOR_CREATE,
    FLAVOR_LIST,
    FLAVOR_GET,
    FLAVOR_UPDATE,
    FLAVOR_DELETE,
) = (
    'flavor_create',
    'flavor_list',
    'flavor_get',
    'flavor_update',
    'flavor_delete',
)

RETRY_OPS = (
    RETRIES_WITH_NO_DELAY,
    MINIMUM_DELAY_RETRIES,
    MINIMUM_DELAY,
    MAXIMUM_DELAY,
    MAXIMUM_DELA_RETRIES,
    LINEAR_INTERVAL,
) = (
    3,
    3,
    5,
    30,
    3,
    5,
)

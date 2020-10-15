# Copyright (c) 2014 Prashanth Raghu.
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

import functools
import sys
import time

from oslo_log import log as logging
from oslo_utils import encodeutils
import redis

from zaqar.storage import errors

LOG = logging.getLogger(__name__)
MESSAGE_IDS_SUFFIX = 'messages'
SUBSCRIPTION_IDS_SUFFIX = 'subscriptions'
FLAVORS_IDS_SUFFIX = 'flavors'
POOLS_IDS_SUFFIX = 'pools'


def descope_queue_name(scoped_name):
    """Descope Queue name with '.'.

    Returns the queue name from the scoped name
    which is of the form project-id.queue-name
    """

    return scoped_name.split('.')[1]


def normalize_none_str(string_or_none):
    """Returns '' IFF given value is None, passthrough otherwise.

    This function normalizes None to the empty string to facilitate
    string concatenation when a variable could be None.
    """

    # TODO(prashanthr_) : Try to reuse this utility. Violates DRY
    return '' if string_or_none is None else string_or_none


def scope_queue_name(queue=None, project=None):
    """Returns a scoped name for a queue based on project and queue.

    If only the project name is specified, a scope signifying "all queues"
    for that project is returned. If neither queue nor project are
    specified, a scope for "all global queues" is returned, which
    is to be interpreted as excluding queues scoped by project.

    :returns: '{project}.{queue}' if project and queue are given,
        '{project}.' if ONLY project is given, '.{queue}' if ONLY
        queue is given, and '.' if neither are given.
    """

    # TODO(prashanthr_) : Try to reuse this utility. Violates DRY
    return normalize_none_str(project) + '.' + normalize_none_str(queue)


# NOTE(prashanthr_): Aliase the scope_queue_name function
# to be used in the pools and claims controller as similar
# functionality is required to scope redis id's.
scope_pool_catalogue = scope_claim_messages = scope_queue_name


def scope_message_ids_set(queue=None, project=None, message_suffix=''):
    """Scope messages set with '.'

    Returns a scoped name for the list of messages in the form
    project-id_queue-name_suffix
    """

    return (normalize_none_str(project) + '.' +
            normalize_none_str(queue) + '.' +
            message_suffix)


def descope_message_ids_set(msgset_key):
    """Descope messages set with '.'

    :returns: (queue, project)
    """

    tokens = msgset_key.split('.')

    return tokens[1] or None, tokens[0] or None


def scope_subscription_ids_set(queue=None, project=None,
                               subscription_suffix=''):
    """Scope subscriptions set with '.'

    Returns a scoped name for the list of subscriptions in the form
    project-id_queue-name_suffix
    """

    return (normalize_none_str(project) + '.' +
            normalize_none_str(queue) + '.' +
            subscription_suffix)


def descope_subscription_ids_set(subset_key):
    """Descope subscriptions set with '.'

    :returns: (queue, project)
    """

    tokens = subset_key.split('.')

    return (tokens[1] or None, tokens[0] or None)


# NOTE(prashanthr_): Aliasing the scope_message_ids_set function
# to be used in the pools and claims controller as similar
# functionality is required to scope redis id's.
scope_queue_catalogue = scope_claims_set = scope_message_ids_set
scope_queue_index = scope_message_ids_set


def msgset_key(queue, project=None):
    return scope_message_ids_set(queue, project, MESSAGE_IDS_SUFFIX)


def subset_key(queue, project=None):
    return scope_subscription_ids_set(queue, project, SUBSCRIPTION_IDS_SUFFIX)


def raises_conn_error(func):
    """Handles the Redis ConnectionFailure error.

    This decorator catches Redis's ConnectionError
    and raises Zaqar's ConnectionError instead.
    """

    # Note(prashanthr_) : Try to reuse this utility. Violates DRY
    # Can pass exception type into the decorator and create a
    # storage level utility.

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.exceptions.ConnectionError:
            LOG.exception('Connection failure:')
            raise errors.ConnectionError()

    return wrapper


def retries_on_connection_error(func):
    """Causes the wrapped function to be re-called on ConnectionError.

    This decorator catches Redis ConnectionError and retries
    the function call.

    .. Note::
       Assumes that the decorated function has defined self.driver.redis_cinf
       so that `max_reconnect_attempts` and `reconnect_sleep` can be taken
       into account.

    .. Warning:: The decorated function must be idempotent.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # TODO(prashanthr_) : Try to reuse this utility. Violates DRY
        # Can pass config parameters into the decorator and create a
        # storage level utility.

        max_attemps = self.driver.redis_conf.max_reconnect_attempts
        sleep_sec = self.driver.redis_conf.reconnect_sleep

        for attempt in range(max_attemps):
            try:
                return func(self, *args, **kwargs)

            except redis.exceptions.ConnectionError:
                # NOTE(kgriffs): redis-py will retry once itself,
                # but if the command cannot be sent the second time after
                # disconnecting and reconnecting, the error is raised
                # and we will catch it here.
                #
                # NOTE(kgriffs): When using a sentinel, if a master fails
                # the initial retry will gracefully fail over to the
                # new master if the sentinel failover delay is low enough;
                # if the delay is too long, then redis-py will get a
                # MasterNotFoundError (a subclass of ConnectionError) on
                # it's retry, which will then just get raised and caught
                # here, in which case we will keep retrying until the
                # sentinel completes the failover and stops raising
                # MasterNotFoundError.

                ex = sys.exc_info()[1]
                LOG.warning(u'Caught ConnectionError, retrying the '
                            'call to {0}'.format(func))

                time.sleep(sleep_sec * (2 ** attempt))
        else:
            LOG.error(u'Caught ConnectionError, maximum attempts '
                      'to {0} exceeded.'.format(func))
            raise ex

    return wrapper


def msg_claimed_filter(message, now):
    """Return True IFF the message is currently claimed."""

    return message.claim_id and (now < message.claim_expires)


def msg_delayed_filter(message, now):
    """Return True IFF the message is currently delayed."""

    return now < message.delay_expires


def msg_echo_filter(message, client_uuid):
    """Return True IFF the specified client posted the message."""

    return message.client_uuid == str(client_uuid)


def msg_expired_filter(message, now):
    """Return True IFF the message has expired."""

    return message.expires <= now


class QueueListCursor(object):

    def __init__(self, client, queues, denormalizer):
        self.queue_iter = queues
        self.denormalizer = denormalizer
        self.client = client

    def __iter__(self):
        return self

    @raises_conn_error
    def next(self):
        curr = next(self.queue_iter)
        queue = self.client.hmget(curr, ['c', 'm'])
        return self.denormalizer(queue, encodeutils.safe_decode(curr))

    def __next__(self):
        return self.next()


class SubscriptionListCursor(object):

    def __init__(self, client, subscriptions, denormalizer):
        self.subscription_iter = subscriptions
        self.denormalizer = denormalizer
        self.client = client

    def __iter__(self):
        return self

    @raises_conn_error
    def next(self):
        curr = next(self.subscription_iter)
        subscription = self.client.hmget(curr, ['s', 'u', 't', 'e', 'o', 'c'])
        # NOTE(flwang): The expired subscription will be removed
        # automatically, but the key can't be deleted automatically as well.
        # Though we clean up those expired ids when create new subscription,
        # we still need to filter them out before a new subscription creation.
        if not subscription[0]:
            return self.next()
        return self.denormalizer(subscription, encodeutils.safe_decode(curr))

    def __next__(self):
        return self.next()


def scope_flavors_ids_set(flavors_suffix=''):
    """Scope flavors set with '.'

    Returns a scoped name for the list of flavors in the form
    suffix
    """

    return flavors_suffix


def scope_project_flavors_ids_set(project=None,
                                  flavors_suffix=''):
    """Scope flavors set with '.'

    Returns a scoped name for the list of flavors in the form
    project-id_suffix
    """

    return (normalize_none_str(project) + '.' + flavors_suffix)


def scope_name_flavors_ids_set(name=None,
                               flavors_suffix=''):
    """Scope flavors set with '.'

    Returns a scoped name for the list of flavors in the form
    flavors_name_suffix
    """

    return (normalize_none_str(name) + '.' + flavors_suffix)


def flavor_set_key():
    return scope_flavors_ids_set(FLAVORS_IDS_SUFFIX)


def flavor_project_subset_key(project=None):
    return scope_project_flavors_ids_set(project,
                                         FLAVORS_IDS_SUFFIX)


def flavor_name_hash_key(name=None):
    return scope_name_flavors_ids_set(name,
                                      FLAVORS_IDS_SUFFIX)


class FlavorListCursor(object):

    def __init__(self, client, flavors, denormalizer):
        self.flavor_iter = flavors
        self.denormalizer = denormalizer
        self.client = client

    def __iter__(self):
        return self

    @raises_conn_error
    def next(self):
        curr = next(self.flavor_iter)
        flavor = self.client.hmget(curr, ['f', 'p', 'c'])
        flavor_dict = {}
        flavor_dict['f'] = flavor[0]
        flavor_dict['p'] = flavor[1]
        flavor_dict['c'] = flavor[2]
        return self.denormalizer(flavor_dict)

    def __next__(self):
        return self.next()


def scope_pools_ids_set(pools_suffix=''):
    """Scope pools set with '.'

    Returns a scoped name for the list of pools in the form
    suffix
    """

    return pools_suffix


def scope_flavor_pools_ids_set(flavor=None,
                               pools_suffix=''):
    """Scope pools set with '.'

    Returns a scoped name for the list of pools in the form
    project-id_suffix
    """
    return (normalize_none_str(flavor) + '.' +
            pools_suffix)


def scope_name_pools_ids_set(name=None,
                             pools_suffix=''):
    """Scope pools set with '.'

    Returns a scoped name for the list of pools in the form
    pools_name_suffix
    """
    return (normalize_none_str(name) + '.' +
            pools_suffix)


def pools_set_key():
    return scope_pools_ids_set(POOLS_IDS_SUFFIX)


def pools_subset_key(flavor=None):
    return scope_flavor_pools_ids_set(flavor,
                                      POOLS_IDS_SUFFIX)


def pools_name_hash_key(name=None):
    return scope_name_pools_ids_set(name,
                                    POOLS_IDS_SUFFIX)


class PoolsListCursor(object):

    def __init__(self, client, pools, denormalizer):
        self.pools_iter = pools
        self.denormalizer = denormalizer
        self.client = client

    def __iter__(self):
        return self

    @raises_conn_error
    def next(self):
        curr = next(self.pools_iter)
        pools = self.client.hmget(curr, ['pl', 'u', 'w', 'f', 'o'])
        pool_dict = {}
        pool_dict['pl'] = pools[0]
        pool_dict['u'] = pools[1]
        pool_dict['w'] = pools[2]
        pool_dict['f'] = pools[3]
        pool_dict['o'] = pools[4]
        return self.denormalizer(pool_dict)

    def __next__(self):
        return self.next()

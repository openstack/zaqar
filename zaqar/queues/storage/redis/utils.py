# Copyright (c) 2014 Prashanth Raghu.
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
import uuid

import redis
import six

from zaqar.i18n import _
from zaqar.openstack.common import log as logging
from zaqar.openstack.common import strutils
from zaqar.queues.storage import errors

LOG = logging.getLogger(__name__)


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


def generate_uuid():
    return str(uuid.uuid4())


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

# NOTE(prashanthr_): Aliasing the scope_message_ids_set function
# to be used in the pools and claims controller as similar
# functionality is required to scope redis id's.
scope_queue_catalogue = scope_claims_set = scope_message_ids_set
scope_queue_index = scope_message_ids_set


def raises_conn_error(func):
    """Handles the Redis ConnectionFailure error.

    This decorator catches Redis's ConnectionError
    and raises Marconi's ConnectionError instead.
    """

    # Note(prashanthr_) : Try to reuse this utility. Violates DRY
    # Can pass exception type into the decorator and create a
    # storage level utility.

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except redis.exceptions.ConnectionError as ex:
            LOG.exception(ex)
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
                ex = sys.exc_info()[1]
                LOG.warn(_(u'Caught ConnectionError, retrying the '
                           'call to {0}').format(func))

                time.sleep(sleep_sec * (2 ** attempt))
        else:
            LOG.error(_(u'Caught ConnectionError, maximum attempts '
                        'to {0} exceeded.').format(func))
            raise ex

    return wrapper


def msg_claimed_filter(message, now):
    """Return True IFF the message is currently claimed."""

    return message.claim_id and (now < message.claim_expires)


def msg_echo_filter(message, client_uuid):
    """Return True IFF the specified client posted the message."""

    return message.client_uuid == six.text_type(client_uuid)


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
        return self.denormalizer(queue, strutils.safe_decode(curr))

    def __next__(self):
        return self.next()
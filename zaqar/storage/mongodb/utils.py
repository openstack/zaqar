# Copyright (c) 2013 Red Hat, Inc.
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

from __future__ import division
import binascii
import collections
import datetime
import functools
import random
import time

from bson import errors as berrors
from bson import objectid
from bson import tz_util
from oslo_log import log as logging
from oslo_utils import timeutils
from pymongo import errors

from zaqar.storage import errors as storage_errors


# BSON ObjectId gives TZ-aware datetime, so we generate a
# TZ-aware UNIX epoch for convenience.
EPOCH = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=tz_util.utc)

# NOTE(cpp-cabrera): the authoritative form of project/queue keys.
PROJ_QUEUE_KEY = 'p_q'

LOG = logging.getLogger(__name__)


def cached_gen(iterable):
    """Converts the iterable into a caching generator.

    Returns a proxy that yields each item of iterable, while at
    the same time caching those items in a deque.

    :param iterable: an iterable to wrap in a caching generator

    :returns: (proxy(iterable), cached_items)
    """
    cached_items = collections.deque()

    def generator(iterable):
        for item in iterable:
            cached_items.append(item)
            yield item

    return generator(iterable), cached_items


def calculate_backoff(attempt, max_attempts, max_sleep, max_jitter=0):
    """Calculates backoff time, in seconds, when retrying an operation.

    This function calculates a simple linear backoff time with
    optional jitter, useful for retrying a request under high
    concurrency.

    The result may be passed directly into time.sleep() in order to
    mitigate stampeding herd syndrome and introduce backpressure towards
    the clients, slowing them down.

    :param attempt: current value of the attempt counter (zero-based)
    :param max_attempts: maximum number of attempts that will be tried
    :param max_sleep: maximum sleep value to apply before jitter, assumed
        to be seconds. Fractional seconds are supported to 1 ms
        granularity.
    :param max_jitter: maximum jitter value to add to the baseline sleep
        time. Actual value will be chosen randomly.

    :raises ValueError: if the parameter is not invalid
    :returns: float representing the number of seconds to sleep, within
        the interval [0, max_sleep), determined linearly according to
        the ratio attempt / max_attempts, with optional jitter.
    """

    if max_sleep < 0:
        raise ValueError(u'max_sleep must be >= 0')

    if max_jitter < 0:
        raise ValueError(u'max_jitter must be >= 0')

    if not (0 <= attempt < max_attempts):
        raise ValueError(u'attempt value is out of range')

    ratio = attempt / max_attempts
    backoff_sec = ratio * max_sleep
    jitter_sec = random.random() * max_jitter

    return backoff_sec + jitter_sec


def to_oid(obj):
    """Creates a new ObjectId based on the input.

    Returns None when TypeError or berrors.InvalidId
    is raised by the ObjectId class.

    :param obj: Anything that can be passed as an
        input to `objectid.ObjectId`
    """
    try:
        return objectid.ObjectId(obj)
    except (TypeError, berrors.InvalidId):
        return None


def oid_ts(oid):
    """Converts an ObjectId to a UNIX timestamp.

    :raises TypeError: if oid isn't an ObjectId
    """
    try:
        return timeutils.delta_seconds(EPOCH, oid.generation_time)
    except AttributeError:
        raise TypeError(u'Expected ObjectId and got %s' % type(oid))


def stat_message(message, now):
    """Creates a stat document from the given message, relative to now."""
    msg_id = message['id']
    created = oid_ts(to_oid(msg_id))
    age = now - created

    return {
        'id': msg_id,
        'age': int(age),
        'created': timeutils.iso8601_from_timestamp(created),
    }


def normalize_none_str(string_or_none):
    """Returns '' IFF given value is None, passthrough otherwise.

    This function normalizes None to the empty string to facilitate
    string concatenation when a variable could be None.
    """
    return '' if string_or_none is None else string_or_none


def scope_queue_name(queue=None, project=None):
    """Returns a scoped name for a queue based on project and queue.

    If only the project name is specified, a scope signifying "all queues"
    for that project is returned. If neither queue nor project are
    specified, a scope for "all global queues" is returned, which
    is to be interpreted as excluding queues scoped by project.

    :returns: '{project}/{queue}' if project and queue are given,
        '{project}/' if ONLY project is given, '/{queue}' if ONLY
        queue is given, and '/' if neither are given.
    """

    # NOTE(kgriffs): Concatenation is faster than format, and
    # put project first since it is guaranteed to be unique.
    return normalize_none_str(project) + '/' + normalize_none_str(queue)


def descope_queue_name(scoped_name):
    """Returns the unscoped queue name, given a fully-scoped name."""

    # NOTE(kgriffs): scoped_name can be either '/', '/global-queue-name',
    # or 'project-id/queue-name'.
    return scoped_name.partition('/')[2] or None


def parse_scoped_project_queue(scoped_name):
    """Returns the project and queue name for a scoped catalogue entry.

    :param scoped_name: a project/queue as given by :scope_queue_name:
    :type scoped_name: six.text_type
    :returns: (project, queue)
    :rtype: (six.text_type, six.text_type)
    """
    return scoped_name.split('/')


def scoped_query(queue, project):
    """Returns a dict usable for querying for scoped project/queues.

    :param queue: name of queue to seek
    :type queue: six.text_type
    :param project: namespace
    :type project: six.text_type
    :param key: query key to use
    :type key: six.text_type
    :returns: query to issue
    :rtype: dict
    """
    key = PROJ_QUEUE_KEY
    query = {}
    scoped_name = scope_queue_name(queue, project)

    if not scoped_name.startswith('/'):
        # NOTE(kgriffs): scoped queue, e.g., 'project-id/queue-name'
        project_prefix = '^' + project + '/'
        query[key] = {'$regex': project_prefix, '$gt': scoped_name}
    elif scoped_name == '/':
        # NOTE(kgriffs): list global queues, but exclude scoped ones
        query[key] = {'$regex': '^/'}
    else:
        # NOTE(kgriffs): unscoped queue, e.g., '/my-global-queue'
        query[key] = {'$regex': '^/', '$gt': scoped_name}

    return query


def get_partition(num_partitions, queue, project=None):
    """Get the partition number for a given queue and project.

    Hashes the queue to a partition number. The hash is stable,
    meaning given the same queue name and project ID, the same
    partition number will always be returned. Note also that
    queues will be uniformly distributed across partitions.

    The number of partitions is taken from the "partitions"
    property in the config file, under the [drivers:storage:mongodb]
    section.
    """

    name = project + queue if project is not None else queue

    # NOTE(kgriffs): For small numbers of partitions, crc32 will
    # provide a uniform distribution. This was verified experimentally
    # with up to 100 partitions.
    return binascii.crc32(name.encode('utf-8')) % num_partitions


def raises_conn_error(func):
    """Handles the MongoDB ConnectionFailure error.

    This decorator catches MongoDB's ConnectionFailure
    error and raises Zaqar's ConnectionError instead.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except errors.ConnectionFailure as ex:
            LOG.exception(ex)
            raise storage_errors.ConnectionError()

    return wrapper


def retries_on_autoreconnect(func):
    """Causes the wrapped function to be re-called on AutoReconnect.

    This decorator catches MongoDB's AutoReconnect error and retries
    the function call.

    .. Note::
       Assumes that the decorated function has defined self.driver.mongodb_conf
       so that `max_reconnect_attempts` and `reconnect_sleep` can be taken
       into account.

    .. Warning:: The decorated function must be idempotent.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # TODO(kgriffs): Figure out a way to not have to rely on the
        # presence of `mongodb_conf`
        max_attemps = self.driver.mongodb_conf.max_reconnect_attempts
        sleep_sec = self.driver.mongodb_conf.reconnect_sleep

        last_ex = None
        for attempt in range(max_attemps):
            try:
                return func(self, *args, **kwargs)
                break

            except errors.AutoReconnect as ex:
                LOG.warning(u'Caught AutoReconnect, retrying the '
                            'call to {0}'.format(func))

                last_ex = ex
                time.sleep(sleep_sec * (2 ** attempt))
        else:
            LOG.error(u'Caught AutoReconnect, maximum attempts '
                      'to {0} exceeded.'.format(func))

            raise last_ex

    return wrapper


class HookedCursor(object):

    def __init__(self, cursor, denormalizer):
        self.cursor = cursor
        self.denormalizer = denormalizer

    def __getattr__(self, attr):
        return getattr(self.cursor, attr)

    def __iter__(self):
        return self

    def __len__(self):
        return self.cursor.count(True)

    @raises_conn_error
    def next(self):
        item = next(self.cursor)
        return self.denormalizer(item)

    def __next__(self):
        return self.next()

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

import collections
import datetime
import functools
import random
import re

from bson import errors as berrors
from bson import objectid
from bson import tz_util
from pymongo import errors

from marconi.common import exceptions
import marconi.openstack.common.log as logging
from marconi.openstack.common import timeutils
from marconi.queues.storage import exceptions as storage_exceptions


DUP_MARKER_REGEX = re.compile(r'\$queue_marker.*?:\s(\d+)')

# BSON ObjectId gives TZ-aware datetime, so we generate a
# TZ-aware UNIX epoch for convenience.
EPOCH = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=tz_util.utc)

LOG = logging.getLogger(__name__)


def dup_marker_from_error(error_message):
    """Extracts the duplicate marker from a MongoDB error string.

    :param error_message: raw error message string returned
        by mongod on a duplicate key error.

    :raises: marconi.common.exceptions.PatternNotFound
    :returns: extracted marker as an integer
    """
    match = DUP_MARKER_REGEX.findall(error_message)
    if not match:
        description = (u'Error message could not be parsed: %s' %
                       error_message)
        raise exceptions.PatternNotFound(description)

    return int(match[-1])


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

    return (generator(iterable), cached_items)


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

    :raises: ValueError
    :returns: float representing the number of seconds to sleep, within
        the interval [0, max_sleep), determined linearly according to
        the ratio attempt / max_attempts, with optional jitter.
    """
    if max_attempts < 0:
        raise ValueError(u'max_attempts must be >= 0')

    if max_sleep < 0:
        raise ValueError(u'max_sleep must be >= 0')

    if max_jitter < 0:
        raise ValueError(u'max_jitter must be >= 0')

    if not (0 <= attempt < max_attempts):
        raise ValueError(u'attempt value is out of range')

    ratio = float(attempt) / float(max_attempts)
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
    :raises: TypeError if oid isn't an ObjectId
    """
    try:
        return timeutils.delta_seconds(EPOCH, oid.generation_time)
    except AttributeError:
        raise TypeError(u'Expected ObjectId and got %s' % type(oid))


def stat_message(message, now):
    """Creates a stat document from the given message, relative to now."""
    oid = message['_id']
    created = oid_ts(oid)
    age = created - now

    return {
        'id': str(oid),
        'age': int(age),
        'created': timeutils.iso8601_from_timestamp(created),
    }


def raises_conn_error(func):
    """Handles mongodb ConnectionFailure error

    This decorator catches mongodb's ConnectionFailure
    exceptions and raises Marconi's ConnectionError instead.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except errors.ConnectionFailure as ex:
            # NOTE(flaper87): Raise the error
            LOG.exception(ex)
            msg = u'ConnectionFailure caught'
            raise storage_exceptions.ConnectionError(msg)

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

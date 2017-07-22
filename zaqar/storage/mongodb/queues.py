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

"""Implements the MongoDB storage controller for queues.

Field Mappings:
    In order to reduce the disk / memory space used,
    field names will be, most of the time, the first
    letter of their long name.
"""

from oslo_log import log as logging
from oslo_utils import timeutils
from pymongo.collection import ReturnDocument
import pymongo.errors

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar import storage
from zaqar.storage import errors
from zaqar.storage.mongodb import utils

LOG = logging.getLogger(__name__)

# NOTE(kgriffs): E.g.: 'queuecontroller:exists:5083853/my-queue'
_QUEUE_CACHE_PREFIX = 'queuecontroller:'

# NOTE(kgriffs): This causes some race conditions, but they are
# harmless. If a queue was deleted, but we are still returning
# that it exists, some messages may get inserted without the
# client getting an error. In this case, those messages would
# be orphaned and expire eventually according to their TTL.
#
# What this means for the client is that they have a bug; they
# deleted a queue and then immediately tried to post messages
# to it. If they keep trying to use the queue, they will
# eventually start getting an error, once the cache entry
# expires, which should clue them in on what happened.
#
# TODO(kgriffs): Make dynamic?
_QUEUE_CACHE_TTL = 5


def _queue_exists_key(queue, project=None):
    # NOTE(kgriffs): Use string concatenation for performance,
    # also put project first since it is guaranteed to be
    # unique, which should reduce lookup time.
    return _QUEUE_CACHE_PREFIX + 'exists:' + str(project) + '/' + queue


class QueueController(storage.Queue):
    """Implements queue resource operations using MongoDB.

    Queues are scoped by project, which is prefixed to the
    queue name.

    ::

        Queues:

            Name            Field
            ---------------------
            name         ->   p_q
            msg counter  ->     c
            metadata     ->     m

        Message Counter:

            Name          Field
            -------------------
            value        ->   v
            modified ts  ->   t
    """

    def __init__(self, *args, **kwargs):
        super(QueueController, self).__init__(*args, **kwargs)

        self._cache = self.driver.cache
        self._collection = self.driver.queues_database.queues

        # NOTE(flaper87): This creates a unique index for
        # project and name. Using project as the prefix
        # allows for querying by project and project+name.
        # This is also useful for retrieving the queues list for
        # a specific project, for example. Order matters!
        self._collection.ensure_index([('p_q', 1)], unique=True)

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    def _get_counter(self, name, project=None):
        """Retrieves the current message counter value for a given queue.

        This helper is used to generate monotonic pagination
        markers that are saved as part of the message
        document.

        Note 1: Markers are scoped per-queue and so are *not*
            globally unique or globally ordered.

        Note 2: If two or more requests to this method are made
            in parallel, this method will return the same counter
            value. This is done intentionally so that the caller
            can detect a parallel message post, allowing it to
            mitigate race conditions between producer and
            observer clients.

        :param name: Name of the queue to which the counter is scoped
        :param project: Queue's project
        :returns: current message counter as an integer
        """

        doc = self._collection.find_one(_get_scoped_query(name, project),
                                        projection={'c.v': 1, '_id': 0})

        if doc is None:
            raise errors.QueueDoesNotExist(name, project)

        return doc['c']['v']

    def _inc_counter(self, name, project=None, amount=1, window=None):
        """Increments the message counter and returns the new value.

        :param name: Name of the queue to which the counter is scoped
        :param project: Queue's project name
        :param amount: (Default 1) Amount by which to increment the counter
        :param window: (Default None) A time window, in seconds, that
            must have elapsed since the counter was last updated, in
            order to increment the counter.

        :returns: Updated message counter value, or None if window
            was specified, and the counter has already been updated
            within the specified time period.

        :raises QueueDoesNotExist: if not found
        """
        now = timeutils.utcnow_ts()

        update = {'$inc': {'c.v': amount}, '$set': {'c.t': now}}
        query = _get_scoped_query(name, project)
        if window is not None:
            threshold = now - window
            query['c.t'] = {'$lt': threshold}

        while True:
            try:
                doc = self._collection.find_one_and_update(
                    query, update, return_document=ReturnDocument.AFTER,
                    projection={'c.v': 1, '_id': 0})

                break
            except pymongo.errors.AutoReconnect as ex:
                LOG.exception(ex)

        if doc is None:
            if window is None:
                # NOTE(kgriffs): Since we did not filter by a time window,
                # the queue should have been found and updated. Perhaps
                # the queue has been deleted?
                message = _(u'Failed to increment the message '
                            u'counter for queue %(name)s and '
                            u'project %(project)s')
                message %= dict(name=name, project=project)

                LOG.warning(message)

                raise errors.QueueDoesNotExist(name, project)

            # NOTE(kgriffs): Assume the queue existed, but the counter
            # was recently updated, causing the range query on 'c.t' to
            # exclude the record.
            return None

        return doc['c']['v']

    # ----------------------------------------------------------------------
    # Interface
    # ----------------------------------------------------------------------

    def _get(self, name, project=None):
        try:
            return self.get_metadata(name, project)
        except errors.QueueDoesNotExist:
            return {}

    def _list(self, project=None, marker=None,
              limit=storage.DEFAULT_QUEUES_PER_PAGE, detailed=False):

        query = utils.scoped_query(marker, project)

        projection = {'p_q': 1, '_id': 0}
        if detailed:
            projection['m'] = 1

        cursor = self._collection.find(query, projection=projection)
        cursor = cursor.limit(limit).sort('p_q')
        marker_name = {}

        def normalizer(record):
            queue = {'name': utils.descope_queue_name(record['p_q'])}
            marker_name['next'] = queue['name']
            if detailed:
                queue['metadata'] = record['m']
            return queue

        yield utils.HookedCursor(cursor, normalizer)
        yield marker_name and marker_name['next']

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def get_metadata(self, name, project=None):
        queue = self._collection.find_one(_get_scoped_query(name, project),
                                          projection={'m': 1, '_id': 0})
        if queue is None:
            raise errors.QueueDoesNotExist(name, project)

        return queue.get('m', {})

    @utils.raises_conn_error
    # @utils.retries_on_autoreconnect
    def _create(self, name, metadata=None, project=None):
        # NOTE(flaper87): If the connection fails after it was called
        # and we retry to insert the queue, we could end up returning
        # `False` because of the `DuplicatedKeyError` although the
        # queue was indeed created by this API call.
        #
        # TODO(kgriffs): Commented out `retries_on_autoreconnect` for
        # now due to the above issue, since creating a queue is less
        # important to make super HA.

        try:
            # NOTE(kgriffs): Start counting at 1, and assume the first
            # message ever posted will succeed and set t to a UNIX
            # "modified at" timestamp.
            counter = {'v': 1, 't': 0}

            scoped_name = utils.scope_queue_name(name, project)
            self._collection.insert_one(
                {'p_q': scoped_name, 'm': metadata or {},
                 'c': counter})

        except pymongo.errors.DuplicateKeyError:
            return False
        else:
            return True

    # NOTE(kgriffs): Only cache when it exists; if it doesn't exist, and
    # someone creates it, we want it to be immediately visible.
    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    @decorators.caches(_queue_exists_key, _QUEUE_CACHE_TTL, lambda v: v)
    def _exists(self, name, project=None):
        query = _get_scoped_query(name, project)
        return self._collection.find_one(query) is not None

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def set_metadata(self, name, metadata, project=None):
        rst = self._collection.update_one(_get_scoped_query(name, project),
                                          {'$set': {'m': metadata}})

        if rst.matched_count == 0:
            raise errors.QueueDoesNotExist(name, project)

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    @_exists.purges
    def _delete(self, name, project=None):
        self._collection.delete_one(_get_scoped_query(name, project))

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def _stats(self, name, project=None):
        pass


def _get_scoped_query(name, project):
    return {'p_q': utils.scope_queue_name(name, project)}

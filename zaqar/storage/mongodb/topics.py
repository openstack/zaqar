# Copyright (c) 2019 Red Hat, Inc.
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

"""Implements the MongoDB storage controller for topics.

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

# NOTE(wanghao): Keep this as same as queues'
_TOPIC_CACHE_PREFIX = 'topiccontroller:'
_TOPIC_CACHE_TTL = 5


def _topic_exists_key(topic, project=None):
    # NOTE(kgriffs): Use string concatenation for performance,
    # also put project first since it is guaranteed to be
    # unique, which should reduce lookup time.
    return _TOPIC_CACHE_PREFIX + 'exists:' + str(project) + '/' + topic


class TopicController(storage.Topic):
    """Implements Topic resource operations using MongoDB.

    Topics are scoped by project, which is prefixed to the
    topic name.

    ::

        Topic:

            Name            Field
            ---------------------
            name         ->   p_t
            msg counter  ->     c
            metadata     ->     m

        Message Counter:

            Name          Field
            -------------------
            value        ->   v
            modified ts  ->   t
    """

    def __init__(self, *args, **kwargs):
        super(TopicController, self).__init__(*args, **kwargs)

        self._cache = self.driver.cache
        self._collection = self.driver.topics_database.topics

        # NOTE(flaper87): This creates a unique index for
        # project and name. Using project as the prefix
        # allows for querying by project and project+name.
        # This is also useful for retrieving the queues list for
        # a specific project, for example. Order matters!
        self._collection.create_index([('p_t', 1)], unique=True)

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    def _get_counter(self, name, project=None):
        """Retrieves the current message counter value for a given topic.

        This helper is used to generate monotonic pagination
        markers that are saved as part of the message
        document.

        Note 1: Markers are scoped per-topic and so are *not*
            globally unique or globally ordered.

        Note 2: If two or more requests to this method are made
            in parallel, this method will return the same counter
            value. This is done intentionally so that the caller
            can detect a parallel message post, allowing it to
            mitigate race conditions between producer and
            observer clients.

        :param name: Name of the queue to which the counter is scoped
        :param project: Topic's project
        :returns: current message counter as an integer
        """

        doc = self._collection.find_one(_get_scoped_query(name, project),
                                        projection={'c.v': 1, '_id': 0})

        if doc is None:
            raise errors.TopicDoesNotExist(name, project)

        return doc['c']['v']

    def _inc_counter(self, name, project=None, amount=1, window=None):
        """Increments the message counter and returns the new value.

        :param name: Name of the topic to which the counter is scoped
        :param project: Topic's project name
        :param amount: (Default 1) Amount by which to increment the counter
        :param window: (Default None) A time window, in seconds, that
            must have elapsed since the counter was last updated, in
            order to increment the counter.

        :returns: Updated message counter value, or None if window
            was specified, and the counter has already been updated
            within the specified time period.

        :raises TopicDoesNotExist: if not found
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
            except pymongo.errors.AutoReconnect:
                LOG.exception('Auto reconnect failure')

        if doc is None:
            if window is None:
                # NOTE(kgriffs): Since we did not filter by a time window,
                # the topic should have been found and updated. Perhaps
                # the topic has been deleted?
                message = _(u'Failed to increment the message '
                            u'counter for topic %(name)s and '
                            u'project %(project)s')
                message %= dict(name=name, project=project)

                LOG.warning(message)

                raise errors.TopicDoesNotExist(name, project)

            # NOTE(kgriffs): Assume the topic existed, but the counter
            # was recently updated, causing the range topic on 'c.t' to
            # exclude the record.
            return None

        return doc['c']['v']

    # ----------------------------------------------------------------------
    # Interface
    # ----------------------------------------------------------------------

    def _get(self, name, project=None):
        try:
            return self.get_metadata(name, project)
        except errors.TopicDoesNotExist:
            return {}

    def _list(self, project=None, kfilter={}, marker=None,
              limit=storage.DEFAULT_TOPICS_PER_PAGE, detailed=False,
              name=None):

        query = utils.scoped_query(marker, project, name, kfilter,
                                   key_value='p_t')

        projection = {'p_t': 1, '_id': 0}
        if detailed:
            projection['m'] = 1

        cursor = self._collection.find(query, projection=projection)
        cursor = cursor.limit(limit).sort('p_t')
        marker_name = {}
        ntotal = self._collection.count_documents(query, limit=limit)

        def normalizer(record):
            topic = {'name': utils.descope_queue_name(record['p_t'])}
            marker_name['next'] = topic['name']
            if detailed:
                topic['metadata'] = record['m']
            return topic

        yield utils.HookedCursor(cursor, normalizer, ntotal=ntotal)
        yield marker_name and marker_name['next']

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def get_metadata(self, name, project=None):
        queue = self._collection.find_one(_get_scoped_query(name, project),
                                          projection={'m': 1, '_id': 0})
        if queue is None:
            raise errors.TopicDoesNotExist(name, project)

        return queue.get('m', {})

    @utils.raises_conn_error
    # @utils.retries_on_autoreconnect
    def _create(self, name, metadata=None, project=None):
        # NOTE(flaper87): If the connection fails after it was called
        # and we retry to insert the topic, we could end up returning
        # `False` because of the `DuplicatedKeyError` although the
        # topic was indeed created by this API call.
        #
        # TODO(kgriffs): Commented out `retries_on_autoreconnect` for
        # now due to the above issue, since creating a topic is less
        # important to make super HA.

        try:
            # NOTE(kgriffs): Start counting at 1, and assume the first
            # message ever posted will succeed and set t to a UNIX
            # "modified at" timestamp.
            counter = {'v': 1, 't': 0}

            scoped_name = utils.scope_queue_name(name, project)
            self._collection.insert_one(
                {'p_t': scoped_name, 'm': metadata or {},
                 'c': counter})

        except pymongo.errors.DuplicateKeyError:
            return False
        else:
            return True

    # NOTE(kgriffs): Only cache when it exists; if it doesn't exist, and
    # someone creates it, we want it to be immediately visible.
    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    @decorators.caches(_topic_exists_key, _TOPIC_CACHE_TTL, lambda v: v)
    def _exists(self, name, project=None):
        query = _get_scoped_query(name, project)
        return self._collection.find_one(query) is not None

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def set_metadata(self, name, metadata, project=None):
        rst = self._collection.update_one(_get_scoped_query(name, project),
                                          {'$set': {'m': metadata}})

        if rst.matched_count == 0:
            raise errors.TopicDoesNotExist(name, project)

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
    return {'p_t': utils.scope_queue_name(name, project)}

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

import pymongo.errors

import marconi.openstack.common.log as logging
from marconi.openstack.common import timeutils
from marconi.queues import storage
from marconi.queues.storage import errors
from marconi.queues.storage.mongodb import utils


LOG = logging.getLogger(__name__)


class QueueController(storage.QueueBase):
    """Implements queue resource operations using MongoDB.

    Queues are scoped by project, which is prefixed to the
    queue name.

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

        self._collection = self.driver.queues_database.queues

        # NOTE(flaper87): This creates a unique index for
        # project and name. Using project as the prefix
        # allows for querying by project and project+name.
        # This is also useful for retrieving the queues list for
        # a specific project, for example. Order matters!
        self._collection.ensure_index([('p_q', 1)], unique=True)

    #-----------------------------------------------------------------------
    # Helpers
    #-----------------------------------------------------------------------

    def _get(self, name, project=None, fields={'m': 1, '_id': 0}):
        queue = self._collection.find_one(_get_scoped_query(name, project),
                                          fields=fields)
        if queue is None:
            raise errors.QueueDoesNotExist(name, project)

        return queue

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
                                        fields={'c.v': 1, '_id': 0})

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

        :raises: storage.errors.QueueDoesNotExist
        """
        now = timeutils.utcnow_ts()

        update = {'$inc': {'c.v': amount}, '$set': {'c.t': now}}
        query = _get_scoped_query(name, project)
        if window is not None:
            threshold = now - window
            query['c.t'] = {'$lt': threshold}

        while True:
            try:
                doc = self._collection.find_and_modify(
                    query, update, new=True, fields={'c.v': 1, '_id': 0})

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

    #-----------------------------------------------------------------------
    # Interface
    #-----------------------------------------------------------------------

    def list(self, project=None, marker=None,
             limit=None, detailed=False):

        if limit is None:
            limit = self.driver.limits_conf.default_queue_paging

        query = utils.scoped_query(marker, project)

        fields = {'p_q': 1, '_id': 0}
        if detailed:
            fields['m'] = 1

        cursor = self._collection.find(query, fields=fields)
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
    def get_metadata(self, name, project=None):
        queue = self._get(name, project)
        return queue.get('m', {})

    @utils.raises_conn_error
    def create(self, name, project=None):
        try:
            # NOTE(kgriffs): Start counting at 1, and assume the first
            # message ever posted will succeed and set t to a UNIX
            # "modified at" timestamp.
            counter = {'v': 1, 't': 0}

            scoped_name = utils.scope_queue_name(name, project)
            self._collection.insert({'p_q': scoped_name, 'm': {},
                                     'c': counter})

        except pymongo.errors.DuplicateKeyError:
            return False
        else:
            return True

    @utils.raises_conn_error
    def exists(self, name, project=None):
        query = _get_scoped_query(name, project)
        return self._collection.find_one(query) is not None

    @utils.raises_conn_error
    def set_metadata(self, name, metadata, project=None):
        rst = self._collection.update(_get_scoped_query(name, project),
                                      {'$set': {'m': metadata}},
                                      multi=False,
                                      manipulate=False)

        if not rst['updatedExisting']:
            raise errors.QueueDoesNotExist(name, project)

    @utils.raises_conn_error
    def delete(self, name, project=None):
        self.driver.message_controller._purge_queue(name, project)
        self._collection.remove(_get_scoped_query(name, project))

    @utils.raises_conn_error
    def stats(self, name, project=None):
        if not self.exists(name, project=project):
            raise errors.QueueDoesNotExist(name, project)

        controller = self.driver.message_controller

        active = controller._count(name, project=project,
                                   include_claimed=False)
        total = controller._count(name, project=project,
                                  include_claimed=True)

        message_stats = {
            'claimed': total - active,
            'free': active,
            'total': total,
        }

        try:
            oldest = controller.first(name, project=project, sort=1)
            newest = controller.first(name, project=project, sort=-1)
        except errors.QueueIsEmpty:
            pass
        else:
            now = timeutils.utcnow_ts()
            message_stats['oldest'] = utils.stat_message(oldest, now)
            message_stats['newest'] = utils.stat_message(newest, now)

        return {'messages': message_stats}


def _get_scoped_query(name, project):
    return {'p_q': utils.scope_queue_name(name, project)}

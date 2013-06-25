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

"""Implements the MongoDB storage controller for claims.

Field Mappings:
    In order to reduce the disk / memory space used,
    field names will be, most of the time, the first
    letter of their long name.
"""

import datetime

from bson import objectid

import marconi.openstack.common.log as logging
from marconi.openstack.common import timeutils
from marconi import storage
from marconi.storage import exceptions
from marconi.storage.mongodb import utils


LOG = logging.getLogger(__name__)


class ClaimController(storage.ClaimBase):
    """Implements claim resource operations using MongoDB.

    No dedicated collection is being used
    for claims.

    Claims are created in the messages
    collection and live within messages, that is,
    in the c field.

    This implementation certainly uses more space
    on disk but reduces the number of queries to
    be executed and the time needed to retrieve
    claims and claimed messages.

    As for the memory usage, this implementation
    requires less memory since a single index is
    required. The index is a compound index between
    the claim id and it's expiration timestamp.
    """

    def _get_queue_id(self, queue, project):
        queue_controller = self.driver.queue_controller
        return queue_controller._get_id(queue, project)

    def get(self, queue, claim_id, project=None):
        msg_ctrl = self.driver.message_controller

        # Check whether the queue exists or not
        qid = self._get_queue_id(queue, project)

        # Base query, always check expire time
        now = timeutils.utcnow()

        try:
            cid = utils.to_oid(claim_id)
        except ValueError:
            raise exceptions.ClaimDoesNotExist()

        age = now - utils.oid_utc(cid)

        def messages(msg_iter):
            msg = msg_iter.next()
            yield msg.pop('claim')
            yield msg

            # Smoke it!
            for msg in msg_iter:
                del msg['claim']
                yield msg

        try:
            # Lets get claim's data
            # from the first message
            # in the iterator
            messages = messages(msg_ctrl.claimed(qid, cid, now))
            claim = messages.next()
            claim = {
                'age': age.seconds,
                'ttl': claim.pop('t'),
                'id': str(claim['id']),
            }
        except StopIteration:
            raise exceptions.ClaimDoesNotExist(cid, queue, project)

        return (claim, messages)

    def create(self, queue, metadata, project=None, limit=10):
        """Creates a claim.

        This implementation was done in a best-effort fashion.
        In order to create a claim we need to get a list
        of messages that can be claimed. Once we have that
        list we execute a query filtering by the ids returned
        by the previous query.

        Since there's a lot of space for race conditions here,
        we'll check if the number of updated records is equal to
        the max number of messages to claim. If the number of updated
        messages is lower than limit we'll try to claim the remaining
        number of messages.

        This 2 queries are required because there's no way, as for the
        time being, to executed an update on a limited number of records
        """
        msg_ctrl = self.driver.message_controller

        # We don't need the qid here but
        # we need to verify it exists.
        qid = self._get_queue_id(queue, project)

        ttl = int(metadata.get('ttl', 60))
        oid = objectid.ObjectId()

        now = timeutils.utcnow()
        ttl_delta = datetime.timedelta(seconds=ttl)
        expires = now + ttl_delta

        meta = {
            'id': oid,
            't': ttl,
            'e': expires,
        }

        # Get a list of active, not claimed nor expired
        # messages that could be claimed.
        msgs = msg_ctrl.active(qid, fields={'_id': 1})
        msgs = msgs.limit(limit).sort('_id')

        messages = iter([])

        # Lets respect the limit
        # during the count
        if msgs.count(True) == 0:
            return (str(oid), messages)

        ids = [msg['_id'] for msg in msgs]
        now = timeutils.utcnow()

        # Set claim field for messages in ids
        updated = msg_ctrl._col.update({'_id': {'$in': ids},
                                        '$or': [
                                            {'c.id': None},
                                            {
                                                'c.id': {'$ne': None},
                                                'c.e': {'$lte': now}
                                            }
                                        ]},
                                       {'$set': {'c': meta}}, upsert=False,
                                       multi=True)['n']

        # NOTE(flaper87): Dirty hack!
        # This sets the expiration time to
        # `expires` on messages that would
        # expire before claim.
        msg_ctrl._col.update({'q': queue,
                              'e': {'$lt': expires},
                              'c.id': oid},
                             {'$set': {'e': expires, 't': ttl}},
                             upsert=False, multi=True)

        if updated != 0:
            claim, messages = self.get(queue, oid, project=project)
        return (str(oid), messages)

    def update(self, queue, claim_id, metadata, project=None):
        try:
            cid = utils.to_oid(claim_id)
        except ValueError:
            raise exceptions.ClaimDoesNotExist(claim_id, queue, project)

        now = timeutils.utcnow()
        ttl = int(metadata.get('ttl', 60))
        ttl_delta = datetime.timedelta(seconds=ttl)

        expires = now + ttl_delta

        if now > expires:
            msg = _('New ttl will make the claim expires')
            raise ValueError(msg)

        qid = self._get_queue_id(queue, project)
        msg_ctrl = self.driver.message_controller
        claimed = msg_ctrl.claimed(qid, cid, expires=now, limit=1)

        try:
            claimed.next()
        except StopIteration:
            raise exceptions.ClaimDoesNotExist(claim_id, queue, project)

        meta = {
            'id': cid,
            't': ttl,
            'e': expires,
        }

        msg_ctrl._col.update({'q': qid, 'c.id': cid},
                             {'$set': {'c': meta}},
                             upsert=False, multi=True)

        # NOTE(flaper87): Dirty hack!
        # This sets the expiration time to
        # `expires` on messages that would
        # expire before claim.
        msg_ctrl._col.update({'q': qid,
                              'e': {'$lt': expires},
                              'c.id': cid},
                             {'$set': {'e': expires, 't': ttl}},
                             upsert=False, multi=True)

    def delete(self, queue, claim_id, project=None):
        msg_ctrl = self.driver.message_controller
        msg_ctrl.unclaim(claim_id)

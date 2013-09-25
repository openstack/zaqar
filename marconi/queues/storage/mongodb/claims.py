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

from bson import objectid

from marconi.common import config
import marconi.openstack.common.log as logging
from marconi.openstack.common import timeutils
from marconi.queues import storage
from marconi.queues.storage import exceptions
from marconi.queues.storage.mongodb import utils

LOG = logging.getLogger(__name__)
CFG = config.namespace('limits:storage').from_options(
    default_message_paging=10,
)


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

    @utils.raises_conn_error
    def get(self, queue, claim_id, project=None):
        msg_ctrl = self.driver.message_controller

        # Base query, always check expire time
        now = timeutils.utcnow_ts()
        cid = utils.to_oid(claim_id)
        if cid is None:
            raise exceptions.ClaimDoesNotExist(queue, project, claim_id)

        def messages(msg_iter):
            msg = next(msg_iter)
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
            msgs = messages(msg_ctrl.claimed(queue, cid, now,
                                             project=project))
            claim = next(msgs)

            update_time = claim['e'] - claim['t']
            age = update_time - now

            claim = {
                'age': int(age),
                'ttl': claim.pop('t'),
                'id': str(claim['id']),
            }
        except StopIteration:
            raise exceptions.ClaimDoesNotExist(cid, queue, project)

        return (claim, msgs)

    @utils.raises_conn_error
    def create(self, queue, metadata, project=None, limit=None):
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
        time being, to execute an update on a limited number of records.
        """
        msg_ctrl = self.driver.message_controller

        if limit is None:
            limit = CFG.default_message_paging

        ttl = metadata['ttl']
        grace = metadata['grace']
        oid = objectid.ObjectId()

        now = timeutils.utcnow_ts()
        claim_expires = now + ttl

        message_expires = claim_expires + grace
        message_ttl = ttl + grace

        meta = {
            'id': oid,
            't': ttl,
            'e': claim_expires,
        }

        # Get a list of active, not claimed nor expired
        # messages that could be claimed.
        msgs = msg_ctrl.active(queue, fields={'_id': 1}, project=project,
                               limit=limit)

        messages = iter([])
        ids = [msg['_id'] for msg in msgs]

        if len(ids) == 0:
            return (None, messages)

        now = timeutils.utcnow_ts()

        # NOTE(kgriffs): Set the claim field for
        # the active message batch, while also
        # filtering out any messages that happened
        # to get claimed just now by one or more
        # parallel requests.
        #
        # Filtering by just 'c.e' works because
        # new messages have that field initialized
        # to the current time when the message is
        # posted. There is no need to check whether
        # 'c' exists or 'c.id' is None.
        updated = msg_ctrl._col.update({'_id': {'$in': ids},
                                        'c.e': {'$lte': now}},
                                       {'$set': {'c': meta}}, upsert=False,
                                       multi=True)['n']

        # NOTE(flaper87): Dirty hack!
        # This sets the expiration time to
        # `expires` on messages that would
        # expire before claim.
        new_values = {'e': message_expires, 't': message_ttl}
        msg_ctrl._col.update({'q': queue,
                              'p': project,
                              'e': {'$lt': message_expires},
                              'c.id': oid},
                             {'$set': new_values},
                             upsert=False, multi=True)

        if updated != 0:
            # NOTE(kgriffs): This extra step is necessary because
            # in between having gotten a list of active messages
            # and updating them, some of them may have been
            # claimed by a parallel request. Therefore, we need
            # to find out which messages were actually tagged
            # with the claim ID successfully.
            claim, messages = self.get(queue, oid, project=project)

        return (str(oid), messages)

    @utils.raises_conn_error
    def update(self, queue, claim_id, metadata, project=None):
        cid = utils.to_oid(claim_id)
        if cid is None:
            raise exceptions.ClaimDoesNotExist(claim_id, queue, project)

        now = timeutils.utcnow_ts()
        ttl = int(metadata.get('ttl', 60))
        expires = now + ttl

        msg_ctrl = self.driver.message_controller
        claimed = msg_ctrl.claimed(queue, cid, expires=now,
                                   limit=1, project=project)

        try:
            next(claimed)
        except StopIteration:
            raise exceptions.ClaimDoesNotExist(claim_id, queue, project)

        meta = {
            'id': cid,
            't': ttl,
            'e': expires,
        }

        msg_ctrl._col.update({'q': queue, 'p': project, 'c.id': cid},
                             {'$set': {'c': meta}},
                             upsert=False, multi=True)

        # NOTE(flaper87): Dirty hack!
        # This sets the expiration time to
        # `expires` on messages that would
        # expire before claim.
        msg_ctrl._col.update({'q': queue,
                              'p': project,
                              'e': {'$lt': expires},
                              'c.id': cid},
                             {'$set': {'e': expires, 't': ttl}},
                             upsert=False, multi=True)

    @utils.raises_conn_error
    def delete(self, queue, claim_id, project=None):
        msg_ctrl = self.driver.message_controller
        msg_ctrl.unclaim(queue, claim_id, project=project)

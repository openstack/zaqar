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
from oslo_log import log as logging
from oslo_utils import timeutils
from pymongo.collection import ReturnDocument

from zaqar import storage
from zaqar.storage import errors
from zaqar.storage.mongodb import utils

LOG = logging.getLogger(__name__)


def _messages_iter(msg_iter):
    """Used to iterate through messages."""

    msg = next(msg_iter)
    yield msg.pop('claim')
    yield msg

    # Smoke it!
    for msg in msg_iter:
        del msg['claim']
        yield msg


class ClaimController(storage.Claim):
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
    @utils.retries_on_autoreconnect
    def get(self, queue, claim_id, project=None):
        msg_ctrl = self.driver.message_controller

        # Base query, always check expire time
        now = timeutils.utcnow_ts()
        cid = utils.to_oid(claim_id)
        if cid is None:
            raise errors.ClaimDoesNotExist(claim_id, queue, project)

        try:
            # Lets get claim's data
            # from the first message
            # in the iterator
            msgs = _messages_iter(msg_ctrl._claimed(queue, cid, now,
                                                    project=project))
            claim = next(msgs)

            update_time = claim['e'] - claim['t']
            age = now - update_time

            claim_meta = {
                'age': int(age),
                'ttl': claim['t'],
                'id': str(claim['id']),
            }
        except StopIteration:
            raise errors.ClaimDoesNotExist(cid, queue, project)

        return claim_meta, msgs

    # NOTE(kgriffs): If we get an autoreconnect or any other connection error,
    # the worst that can happen is you get an orphaned claim, but it will
    # expire eventually and free up those messages to be claimed again. We
    # might consider setting a "claim valid" flag similar to how posting
    # messages works, in order to avoid this situation if it turns out to
    # be a real problem for users.
    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def create(self, queue, metadata, project=None,
               limit=storage.DEFAULT_MESSAGES_PER_CLAIM):
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
        queue_ctrl = self.driver.queue_controller

        ttl = metadata['ttl']
        grace = metadata['grace']
        oid = objectid.ObjectId()

        now = timeutils.utcnow_ts()
        claim_expires = now + ttl
        claim_expires_dt = datetime.datetime.utcfromtimestamp(claim_expires)

        message_ttl = ttl + grace
        message_expiration = datetime.datetime.utcfromtimestamp(
            claim_expires + grace)

        meta = {
            'id': oid,
            't': ttl,
            'e': claim_expires,
            'c': 0   # NOTE(flwang): A placeholder which will be updated later
        }

        # Get a list of active, not claimed nor expired
        # messages that could be claimed.
        msgs = msg_ctrl._active(queue, projection={'_id': 1, 'c': 1},
                                project=project,
                                limit=limit)

        messages = iter([])
        be_claimed = [(msg['_id'], msg['c'].get('c', 0)) for msg in msgs]
        ids = [_id for _id, _ in be_claimed]

        if len(ids) == 0:
            return None, messages

        # Get the maxClaimCount and deadLetterQueue from current queue's meta
        queue_meta = queue_ctrl.get(queue, project=project)

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
        collection = msg_ctrl._collection(queue, project)
        updated = collection.update_many({'_id': {'$in': ids},
                                          'c.e': {'$lte': now}},
                                         {'$set': {'c': meta}},
                                         upsert=False)

        # NOTE(flaper87): Dirty hack!
        # This sets the expiration time to
        # `expires` on messages that would
        # expire before claim.
        new_values = {'e': message_expiration, 't': message_ttl}
        collection.update_many({'p_q': utils.scope_queue_name(queue, project),
                                'e': {'$lt': claim_expires_dt},
                                'c.id': oid},
                               {'$set': new_values},
                               upsert=False)

        msg_count_moved_to_DLQ = 0
        if ('_max_claim_count' in queue_meta and
                '_dead_letter_queue' in queue_meta):
            LOG.debug(u"The list of messages being claimed: %(be_claimed)s",
                      {"be_claimed": be_claimed})

            for _id, claimed_count in be_claimed:
                # NOTE(flwang): We have claimed the message above, but we will
                # update the claim count below. So that means, when the
                # claimed_count equals queue_meta['_max_claim_count'], the
                # message has met the threshold. And Zaqar will move it to the
                # DLQ.
                if claimed_count < queue_meta['_max_claim_count']:
                    # 1. Save the new max claim count for message
                    collection.update_one({'_id': _id,
                                           'c.id': oid},
                                          {'$set': {'c.c': claimed_count + 1}},
                                          upsert=False)
                    LOG.debug(u"Message %(id)s has been claimed %(count)d "
                              u"times.", {"id": str(_id),
                                          "count": claimed_count + 1})
                else:
                    # 2. Check if the message's claim count has exceeded the
                    # max claim count defined in the queue, if so, move the
                    # message to the dead letter queue.

                    # NOTE(flwang): We're moving message directly. That means,
                    # the queue and dead letter queue must be created on the
                    # same storage pool. It's a technical tradeoff, because if
                    # we re-send the message to the dead letter queue by
                    # message controller, then we will lost all the claim
                    # information.
                    dlq_name = queue_meta['_dead_letter_queue']
                    new_msg = {'c.c': claimed_count,
                               'p_q': utils.scope_queue_name(dlq_name,
                                                             project)}
                    dlq_ttl = queue_meta.get("_dead_letter_queue_messages_ttl")
                    if dlq_ttl:
                        new_msg['t'] = dlq_ttl
                    kwargs = {"return_document": ReturnDocument.AFTER}
                    msg = collection.find_one_and_update({'_id': _id,
                                                          'c.id': oid},
                                                         {'$set': new_msg},
                                                         **kwargs)
                    dlq_collection = msg_ctrl._collection(dlq_name, project)
                    if not dlq_collection:
                        LOG.warning(u"Failed to find the message collection "
                                    u"for queue %(dlq_name)s", {"dlq_name":
                                                                dlq_name})
                        return None, iter([])
                    # NOTE(flwang): If dead letter queue and queue are in the
                    # same partition, the message has been already
                    # modified.
                    if collection != dlq_collection:
                        result = dlq_collection.insert_one(msg)
                        if result.inserted_id:
                            collection.delete_one({'_id': _id})
                    LOG.debug(u"Message %(id)s has met the max claim count "
                              u"%(count)d, now it has been moved to dead "
                              u"letter queue %(dlq_name)s.",
                              {"id": str(_id), "count": claimed_count,
                               "dlq_name": dlq_name})
                    msg_count_moved_to_DLQ += 1

        if updated.modified_count != 0:
            # NOTE(kgriffs): This extra step is necessary because
            # in between having gotten a list of active messages
            # and updating them, some of them may have been
            # claimed by a parallel request. Therefore, we need
            # to find out which messages were actually tagged
            # with the claim ID successfully.
            if msg_count_moved_to_DLQ < updated.modified_count:
                claim, messages = self.get(queue, oid, project=project)
            else:
                # NOTE(flwang): Though messages are claimed, but all of them
                # have met the max claim count and have been moved to DLQ.
                return None, iter([])

        return str(oid), messages

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def update(self, queue, claim_id, metadata, project=None):
        cid = utils.to_oid(claim_id)
        if cid is None:
            raise errors.ClaimDoesNotExist(claim_id, queue, project)

        now = timeutils.utcnow_ts()
        grace = metadata['grace']
        ttl = metadata['ttl']
        claim_expires = now + ttl
        claim_expires_dt = datetime.datetime.utcfromtimestamp(claim_expires)
        message_ttl = ttl + grace
        message_expires = datetime.datetime.utcfromtimestamp(
            claim_expires + grace)

        msg_ctrl = self.driver.message_controller
        claimed = msg_ctrl._claimed(queue, cid, expires=now,
                                    limit=1, project=project)

        try:
            next(claimed)
        except StopIteration:
            raise errors.ClaimDoesNotExist(claim_id, queue, project)

        meta = {
            'id': cid,
            't': ttl,
            'e': claim_expires,
        }

        # TODO(kgriffs): Create methods for these so we don't interact
        # with the messages collection directly (loose coupling)
        scope = utils.scope_queue_name(queue, project)
        collection = msg_ctrl._collection(queue, project)
        collection.update_many({'p_q': scope, 'c.id': cid},
                               {'$set': {'c': meta}},
                               upsert=False)

        # NOTE(flaper87): Dirty hack!
        # This sets the expiration time to
        # `expires` on messages that would
        # expire before claim.
        collection.update_many({'p_q': scope,
                                'e': {'$lt': claim_expires_dt},
                                'c.id': cid},
                               {'$set': {'e': message_expires,
                                         't': message_ttl}},
                               upsert=False)

    @utils.raises_conn_error
    @utils.retries_on_autoreconnect
    def delete(self, queue, claim_id, project=None):
        msg_ctrl = self.driver.message_controller
        msg_ctrl._unclaim(queue, claim_id, project=project)

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

import msgpack
from oslo.utils import timeutils
import redis

from zaqar.common import decorators
from zaqar.openstack.common import log as logging
from zaqar.queues import storage
from zaqar.queues.storage import errors
from zaqar.queues.storage.redis import messages
from zaqar.queues.storage.redis import utils

LOG = logging.getLogger(__name__)

QUEUE_CLAIMS_SUFFIX = 'claims'
CLAIM_MESSAGES_SUFFIX = 'messages'

RETRY_CLAIM_TIMEOUT = 10

# NOTE(kgriffs): Number of claims to read at a time when counting
# the total number of claimed messages for a queue.
#
# TODO(kgriffs): Tune this parameter and/or make it configurable. It
# takes  ~0.8 ms to retrieve 100 items from a sorted set on a 2.7 GHz
# Intel Core i7 (not including network latency).
COUNTING_BATCH_SIZE = 100


class ClaimController(storage.Claim):
    """Implements claim resource operations using Redis.

    Redis Data Structures:

    1. Claims list (Redis set) contains claim IDs

        Key: <project_id>.<queue_name>.claims

        +-------------+---------+
        |  Name       |  Field  |
        +=============+=========+
        |  claim_ids  |  m      |
        +-------------+---------+

    2. Claimed Messages (Redis set) contains the list
    of message ids stored per claim

        Key: <claim_id>.messages

    3. Claim info (Redis hash):

        Key: <claim_id>

        +----------------+---------+
        |  Name          |  Field  |
        +================+=========+
        |  ttl           |  t      |
        +----------------+---------+
        |  id            |  id     |
        +----------------+---------+
        |  expires       |  e      |
        +----------------+---------+
        |  num_messages  |  n      |
        +----------------+---------+
    """

    def __init__(self, *args, **kwargs):
        super(ClaimController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection

        self._packer = msgpack.Packer(encoding='utf-8',
                                      use_bin_type=True).pack
        self._unpacker = functools.partial(msgpack.unpackb, encoding='utf-8')

    @decorators.lazy_property(write=False)
    def _message_ctrl(self):
        return self.driver.message_controller

    @decorators.lazy_property(write=False)
    def _queue_ctrl(self):
        return self.driver.queue_controller

    def _get_claim_info(self, claim_id, fields, transform=int):
        """Get one or more fields from the claim Info."""

        values = self._client.hmget(claim_id, fields)
        return [transform(v) for v in values] if transform else values

    def _exists(self, queue, claim_id, project):
        client = self._client
        claims_set_key = utils.scope_claims_set(queue, project,
                                                QUEUE_CLAIMS_SUFFIX)

        # Return False if no such claim exists
        # TODO(prashanthr_): Discuss the feasibility of a bloom filter.
        if client.zscore(claims_set_key, claim_id) is None:
            return False

        expires = self._get_claim_info(claim_id, b'e')[0]
        now = timeutils.utcnow_ts()

        if expires <= now:
            # NOTE(kgriffs): Redis should automatically remove the
            # other records in the very near future. This one
            # has to be manually deleted, however.
            client.zrem(claims_set_key, claim_id)
            return False

        return True

    def _get_claimed_message_keys(self, claim_msgs_key):
        return self._client.lrange(claim_msgs_key, 0, -1)

    def _count_messages(self, queue, project):
        """Count and return the total number of claimed messages."""

        # NOTE(kgriffs): Iterate through all claims, adding up the
        # number of messages per claim. This is obviously slower
        # than keeping a side counter, but is also less error-prone.
        # Plus, it avoids having to do a lot of extra work during
        # garbage collection passes. Also, considering that most
        # workloads won't require a large number of claims, most of
        # the time we can do this in a single pass, so it is still
        # pretty fast.

        claims_set_key = utils.scope_claims_set(queue, project,
                                                QUEUE_CLAIMS_SUFFIX)
        num_claimed = 0
        offset = 0

        while True:
            claim_ids = self._client.zrange(claims_set_key, offset,
                                            offset + COUNTING_BATCH_SIZE - 1)
            if not claim_ids:
                break

            offset += len(claim_ids)

            with self._client.pipeline() as pipe:
                for cid in claim_ids:
                    pipe.hmget(cid, 'n')

                claim_infos = pipe.execute()

            for info in claim_infos:
                # NOTE(kgriffs): In case the claim was deleted out
                # from under us, sanity-check that we got a non-None
                # info list.
                if info:
                    num_claimed += int(info[0])

        return num_claimed

    def _del_message(self, queue, project, claim_id, message_id, pipe):
        """Called by MessageController when messages are being deleted.

        This method removes the message from claim data structures.
        """

        claim_msgs_key = utils.scope_claim_messages(claim_id,
                                                    CLAIM_MESSAGES_SUFFIX)

        # NOTE(kgriffs): In practice, scanning will be quite fast,
        # since the usual pattern is to delete messages from oldest
        # to newest, and the list is sorted in that order. Also,
        # the length of the list will usually be ~10 messages.
        pipe.lrem(claim_msgs_key, 1, message_id)

        # NOTE(kgriffs): Decrement the message counter used for stats
        pipe.hincrby(claim_id, 'n', -1)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _gc(self, queue, project):
        """Garbage-collect expired claim data.

        Not all claim data can be automatically expired. This method
        cleans up the remainder.

        :returns: Number of claims removed
        """

        claims_set_key = utils.scope_claims_set(queue, project,
                                                QUEUE_CLAIMS_SUFFIX)
        now = timeutils.utcnow_ts()
        num_removed = self._client.zremrangebyscore(claims_set_key, 0, now)
        return num_removed

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def get(self, queue, claim_id, project=None):
        if not self._exists(queue, claim_id, project):
            raise errors.ClaimDoesNotExist(queue, project, claim_id)

        claim_msgs_key = utils.scope_claim_messages(claim_id,
                                                    CLAIM_MESSAGES_SUFFIX)

        # basic_messages
        msg_keys = self._get_claimed_message_keys(claim_msgs_key)
        claimed_msgs = messages.Message.from_redis_bulk(msg_keys,
                                                        self._client)
        now = timeutils.utcnow_ts()
        basic_messages = [msg.to_basic(now)
                          for msg in claimed_msgs if msg]

        # claim_meta
        now = timeutils.utcnow_ts()
        expires, ttl = self._get_claim_info(claim_id, [b'e', b't'])
        update_time = expires - ttl
        age = now - update_time

        claim_meta = {
            'age': age,
            'ttl': ttl,
            'id': claim_id,
        }

        return claim_meta, basic_messages

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def create(self, queue, metadata, project=None,
               limit=storage.DEFAULT_MESSAGES_PER_CLAIM):

        claim_ttl = int(metadata.get('ttl', 60))
        grace = int(metadata.get('grace', 60))
        msg_ttl = claim_ttl + grace

        claim_id = utils.generate_uuid()
        claim_msgs_key = utils.scope_claim_messages(claim_id,
                                                    CLAIM_MESSAGES_SUFFIX)

        claims_set_key = utils.scope_claims_set(queue, project,
                                                QUEUE_CLAIMS_SUFFIX)

        with self._client.pipeline() as pipe:
            # NOTE(kgriffs): Retry the operation if another transaction
            # completes before this one, in which case it will have
            # claimed the same messages the current thread is trying
            # to claim, and therefoe we must try for another batch.
            #
            # This loop will eventually time out if we can't manage to
            # claim any messages due to other threads continually beating
            # us to the punch.

            # TODO(kgriffs): Would it be beneficial (or harmful) to
            # introducce a backoff sleep in between retries?

            start_ts = timeutils.utcnow_ts()
            while (timeutils.utcnow_ts() - start_ts) < RETRY_CLAIM_TIMEOUT:

                # NOTE(kgriffs): The algorithm for claiming messages:
                #
                # 1. Get a batch of messages that are currently active.
                # 2. For each active message in the batch, extend its
                #    lifetime IFF it would otherwise expire before the
                #    claim itself does.
                # 3. Associate the claim with each message
                # 4. Create a claim record with details such as TTL
                #    and expiration time.
                # 5. Add the claim's ID to a set to facilitate fast
                #    existence checks.

                try:
                    # TODO(kgriffs): Is it faster/better to do this all
                    # in a Lua script instead of using an app-layer
                    # transaction? Lua requires Redis 2.6 or better.

                    # NOTE(kgriffs): Abort the entire transaction if
                    # another request beats us to the punch. We detect
                    # this by putting a watch on the key that will have
                    # one of its fields updated as the final step of
                    # the transaction.
                    #
                    # No other request to list active messages can
                    # proceed while this current transaction is in
                    # progress; therefore, it is not possible for
                    # a different process to get some active messages
                    # while the pipeline commands have partway
                    # completed. Either the other process will query
                    # for active messages at the same moment as
                    # the current proc and get the exact same set,
                    # or its request will have to wait while the
                    # current process performs the transaction in
                    # its entirety.
                    pipe.watch(claims_set_key)
                    pipe.multi()

                    results = self._message_ctrl._active(
                        queue, project=project, limit=limit)

                    cursor = next(results)
                    msg_list = list(cursor)
                    num_messages = len(msg_list)

                    # NOTE(kgriffs): If there are no active messages to
                    # claim, simply return an empty list.
                    if not msg_list:
                        return (None, iter([]))

                    basic_messages = []

                    now = timeutils.utcnow_ts()

                    claim_expires = now + claim_ttl
                    msg_expires = claim_expires + grace

                    # Associate the claim with each message
                    for msg in msg_list:
                        msg.claim_id = claim_id
                        msg.claim_expires = claim_expires

                        if _msg_would_expire(msg, msg_expires):
                            msg.ttl = msg_ttl
                            msg.expires = msg_expires

                        pipe.rpush(claim_msgs_key, msg.id)

                        # TODO(kgriffs): Rather than writing back the
                        # entire message, only set the fields that
                        # have changed.
                        msg.to_redis(pipe, include_body=False)

                        basic_messages.append(msg.to_basic(now))

                    pipe.expire(claim_msgs_key, claim_ttl)

                    # Create the claim
                    claim_info = {
                        'id': claim_id,
                        't': claim_ttl,
                        'e': claim_expires,
                        'n': num_messages,
                    }

                    pipe.hmset(claim_id, claim_info)
                    pipe.expire(claim_id, claim_ttl)

                    # NOTE(kgriffs): Add the claim ID to a set so that
                    # existence checks can be performed quickly. This
                    # is also used as a watch key in order to gaurd
                    # against race conditions.
                    #
                    # A sorted set is used to facilitate cleaning
                    # up the IDs of expired claims.
                    pipe.zadd(claims_set_key, claim_expires, claim_id)
                    pipe.execute()

                    return claim_id, basic_messages

                except redis.exceptions.WatchError:
                    continue

        raise errors.ClaimConflict(queue, project)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def update(self, queue, claim_id, metadata, project=None):
        if not self._exists(queue, claim_id, project):
            raise errors.ClaimDoesNotExist(claim_id, queue, project)

        now = timeutils.utcnow_ts()

        claim_ttl = int(metadata.get('ttl', 60))
        claim_expires = now + claim_ttl

        grace = int(metadata.get('grace', 60))
        msg_ttl = claim_ttl + grace
        msg_expires = claim_expires + grace

        claim_msgs_key = utils.scope_claim_messages(claim_id,
                                                    CLAIM_MESSAGES_SUFFIX)

        msg_keys = self._get_claimed_message_keys(claim_msgs_key)
        claimed_msgs = messages.MessageEnvelope.from_redis_bulk(msg_keys,
                                                                self._client)
        claim_info = {
            't': claim_ttl,
            'e': claim_expires,
        }

        with self._client.pipeline() as pipe:
            for msg in claimed_msgs:
                if msg:
                    msg.claim_id = claim_id
                    msg.claim_expires = claim_expires

                    if _msg_would_expire(msg, msg_expires):
                        msg.ttl = msg_ttl
                        msg.expires = msg_expires

                    # TODO(kgriffs): Rather than writing back the
                    # entire message, only set the fields that
                    # have changed.
                    #
                    # When this change is made, don't forget to
                    # also call pipe.expire with the new TTL value.
                    msg.to_redis(pipe)

            # Update the claim id and claim expiration info
            # for all the messages.
            pipe.hmset(claim_id, claim_info)
            pipe.expire(claim_id, claim_ttl)

            pipe.expire(claim_msgs_key, claim_ttl)

            claims_set_key = utils.scope_claims_set(queue, project,
                                                    QUEUE_CLAIMS_SUFFIX)

            pipe.zadd(claims_set_key, claim_expires, claim_id)

            pipe.execute()

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def delete(self, queue, claim_id, project=None):
        # NOTE(prashanthr_): Return silently when the claim
        # does not exist
        if not self._exists(queue, claim_id, project):
            return

        now = timeutils.utcnow_ts()
        claim_msgs_key = utils.scope_claim_messages(claim_id,
                                                    CLAIM_MESSAGES_SUFFIX)

        msg_keys = self._get_claimed_message_keys(claim_msgs_key)
        claimed_msgs = messages.MessageEnvelope.from_redis_bulk(msg_keys,
                                                                self._client)
        # Update the claim id and claim expiration info
        # for all the messages.
        claims_set_key = utils.scope_claims_set(queue, project,
                                                QUEUE_CLAIMS_SUFFIX)

        with self._client.pipeline() as pipe:
            pipe.zrem(claims_set_key, claim_id)
            pipe.delete(claim_id)
            pipe.delete(claim_msgs_key)

            for msg in claimed_msgs:
                if msg:
                    msg.claim_id = None
                    msg.claim_expires = now

                    # TODO(kgriffs): Rather than writing back the
                    # entire message, only set the fields that
                    # have changed.
                    msg.to_redis(pipe)

            pipe.execute()


def _msg_would_expire(message, now):
    return message.expires <= now

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
from oslo_utils import timeutils
from oslo_utils import uuidutils

from zaqar.common import decorators
from zaqar import storage
from zaqar.storage import errors
from zaqar.storage.redis import messages
from zaqar.storage.redis import scripting
from zaqar.storage.redis import utils

QUEUE_CLAIMS_SUFFIX = 'claims'
CLAIM_MESSAGES_SUFFIX = 'messages'
# The rank counter is an atomic index to rank messages
# in a FIFO manner.
MESSAGE_RANK_COUNTER_SUFFIX = 'rank_counter'

RETRY_CLAIM_TIMEOUT = 10

# NOTE(kgriffs): Number of claims to read at a time when counting
# the total number of claimed messages for a queue.
#
# TODO(kgriffs): Tune this parameter and/or make it configurable. It
# takes  ~0.8 ms to retrieve 100 items from a sorted set on a 2.7 GHz
# Intel Core i7 (not including network latency).
COUNTING_BATCH_SIZE = 100


class ClaimController(storage.Claim, scripting.Mixin):
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

    script_names = ['claim_messages']

    def __init__(self, *args, **kwargs):
        super(ClaimController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection

        self._packer = msgpack.Packer(encoding='utf-8',
                                      use_bin_type=True).pack
        self._unpacker = functools.partial(msgpack.unpackb, encoding='utf-8')

    @decorators.lazy_property(write=False)
    def _queue_ctrl(self):
        return self.driver.queue_controller

    def _get_claim_info(self, claim_id, fields, transform=int):
        """Get one or more fields from the claim Info."""

        values = self._client.hmget(claim_id, fields)
        if values == [None]:
            return values
        else:
            return [transform(v) for v in values] if transform else values

    def _claim_messages(self, msgset_key, now, limit,
                        claim_id, claim_expires, msg_ttl, msg_expires):

        # NOTE(kgriffs): A watch on a pipe could also be used, but that
        # is less efficient and predictable, based on our experience in
        # having to do something similar in the MongoDB driver.
        func = self._scripts['claim_messages']

        args = [now, limit, claim_id, claim_expires, msg_ttl, msg_expires]
        return func(keys=[msgset_key], args=args)

    def _exists(self, queue, claim_id, project):
        client = self._client
        claims_set_key = utils.scope_claims_set(queue, project,
                                                QUEUE_CLAIMS_SUFFIX)
        # In some cases, the queue maybe doesn't exist. So we should check
        # whether the queue exists. Return False if no such queue exists.

        # Todo(flwang): We should delete all related data after the queue is
        # deleted. See the blueprint for more detail:
        # https://blueprints.launchpad.net/zaqar/+spec/clear-resources-after-delete-queue
        if not self._queue_ctrl._exists(queue, project):
            return False

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
            raise errors.ClaimDoesNotExist(claim_id, queue, project)

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

        queue_ctrl = self.driver.queue_controller
        msg_ctrl = self.driver.message_controller

        claim_ttl = metadata['ttl']
        grace = metadata['grace']

        now = timeutils.utcnow_ts()
        msg_ttl = claim_ttl + grace
        claim_expires = now + claim_ttl
        msg_expires = claim_expires + grace

        # Get the maxClaimCount and deadLetterQueue from current queue's meta
        queue_meta = queue_ctrl.get(queue, project=project)

        claim_id = uuidutils.generate_uuid()
        claimed_msgs = []

        # NOTE(kgriffs): Claim some messages
        msgset_key = utils.msgset_key(queue, project)
        claimed_ids = self._claim_messages(msgset_key, now, limit,
                                           claim_id, claim_expires,
                                           msg_ttl, msg_expires)

        if claimed_ids:
            claimed_msgs = messages.Message.from_redis_bulk(claimed_ids,
                                                            self._client)
            claimed_msgs = [msg.to_basic(now) for msg in claimed_msgs]

            # NOTE(kgriffs): Perist claim records
            with self._client.pipeline() as pipe:
                claim_msgs_key = utils.scope_claim_messages(
                    claim_id, CLAIM_MESSAGES_SUFFIX)

                for mid in claimed_ids:
                    pipe.rpush(claim_msgs_key, mid)

                pipe.expire(claim_msgs_key, claim_ttl)

                claim_info = {
                    'id': claim_id,
                    't': claim_ttl,
                    'e': claim_expires,
                    'n': len(claimed_ids),
                }

                pipe.hmset(claim_id, claim_info)
                pipe.expire(claim_id, claim_ttl)

                # NOTE(kgriffs): Add the claim ID to a set so that
                # existence checks can be performed quickly. This
                # is also used as a watch key in order to guard
                # against race conditions.
                #
                # A sorted set is used to facilitate cleaning
                # up the IDs of expired claims.
                claims_set_key = utils.scope_claims_set(queue, project,
                                                        QUEUE_CLAIMS_SUFFIX)

                pipe.zadd(claims_set_key, claim_expires, claim_id)
                pipe.execute()

                if ('_max_claim_count' in queue_meta and
                        '_dead_letter_queue' in queue_meta):
                    claimed_msgs_removed = []
                    for msg in claimed_msgs:
                        if msg:
                            claimed_count = msg['claim_count']
                            if claimed_count < queue_meta['_max_claim_count']:
                                # 1. Save the new max claim count for message
                                claim_count = claimed_count + 1
                                dic = {"c.c": claim_count}
                                pipe.hmset(msg['id'], dic)
                                pipe.execute()
                            else:
                                # 2. Check if the message's claim count has
                                # exceeded the max claim count defined in the
                                # queue, if so, move the message to the dead
                                # letter queue and modify it's ttl.
                                # NOTE(gengchc):  We're moving message by
                                # moving the message id from queue to dead
                                # letter queue directly.That means, the queue
                                # and dead letter queue must be created on
                                # the same pool.
                                ddl = utils.scope_queue_name(
                                    queue_meta['_dead_letter_queue'], project)
                                ddl_ttl = queue_meta.get(
                                    "_dead_letter_queue_messages_ttl")
                                dic = {"t": msg['ttl']}
                                if ddl_ttl:
                                    dic = {"t": ddl_ttl}
                                pipe.hmset(msg['id'], dic)
                                queueproject = [s for s in ddl.split('.')]
                                msgs_key_ddl = utils.msgset_key(
                                    queueproject[1], queueproject[0])
                                counter_key_ddl = utils.scope_queue_index(
                                    queueproject[1], queueproject[0],
                                    MESSAGE_RANK_COUNTER_SUFFIX)
                                msgs_key = utils.msgset_key(
                                    queue, project=project)
                                pipe.zrem(msgs_key, msg['id'])
                                message_ids = []
                                message_ids.append(msg['id'])
                                msg_ctrl._index_messages(msgs_key_ddl,
                                                         counter_key_ddl,
                                                         message_ids)
                                pipe.execute()
                                # Add dead letter message to
                                # claimed_msgs_removed, finally remove
                                # them from claimed_msgs.
                                claimed_msgs_removed.append(msg)

                    # Remove dead letter messages from claimed_msgs.
                    for msg_remove in claimed_msgs_removed:
                        claimed_msgs.remove(msg_remove)
                    if len(claimed_msgs) == 0:
                        return None, iter([])

        return claim_id, claimed_msgs

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def update(self, queue, claim_id, metadata, project=None):
        if not self._exists(queue, claim_id, project):
            raise errors.ClaimDoesNotExist(claim_id, queue, project)

        now = timeutils.utcnow_ts()

        claim_ttl = metadata['ttl']
        claim_expires = now + claim_ttl

        grace = metadata['grace']
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

                    if _msg_would_expire(msg, claim_expires):
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

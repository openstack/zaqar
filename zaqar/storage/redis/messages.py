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
import uuid

from oslo_utils import encodeutils
from oslo_utils import timeutils
import redis

from zaqar.common import decorators
from zaqar import storage
from zaqar.storage import errors
from zaqar.storage.redis import models
from zaqar.storage.redis import scripting
from zaqar.storage.redis import utils

Message = models.Message
MessageEnvelope = models.MessageEnvelope


MSGSET_INDEX_KEY = 'msgset_index'

# The rank counter is an atomic index to rank messages
# in a FIFO manner.
MESSAGE_RANK_COUNTER_SUFFIX = 'rank_counter'

# NOTE(kgriffs): This value, in seconds, should be at least less than the
# minimum allowed TTL for messages (60 seconds).
RETRY_POST_TIMEOUT = 10

# TODO(kgriffs): Tune this and/or make it configurable. Don't want
# it to be so large that it blocks other operations for more than
# 1-2 milliseconds.
GC_BATCH_SIZE = 100


class MessageController(storage.Message, scripting.Mixin):
    """Implements message resource operations using Redis.

    Messages are scoped by project + queue.

    Redis Data Structures:

    1. Message id's list (Redis sorted set)

        Each queue in the system has a set of message ids currently
        in the queue. The list is sorted based on a ranking which is
        incremented atomically using the counter(MESSAGE_RANK_COUNTER_SUFFIX)
        also stored in the database for every queue.

        Key: <project_id>.<queue_name>.messages

    2. Index of message ID lists (Redis sorted set)

        This is a sorted set that facilitates discovery of all the
        message ID lists. This is necessary when performing
        garbage collection on the IDs contained within these lists.

        Key: msgset_index

    3. Messages(Redis Hash):

        Scoped by the UUID of the message, the redis datastructure
        has the following information.

        +---------------------+---------+
        |  Name               |  Field  |
        +=====================+=========+
        |  id                 |  id     |
        +---------------------+---------+
        |  ttl                |  t      |
        +---------------------+---------+
        |  expires            |  e      |
        +---------------------+---------+
        |  body               |  b      |
        +---------------------+---------+
        |  claim              |  c      |
        +---------------------+---------+
        |  claim expiry time  |  c.e    |
        +---------------------+---------+
        |  claim count        |  c.c    |
        +---------------------+---------+
        |  client uuid        |  u      |
        +---------------------+---------+
        |  created time       |  cr     |
        +---------------------+---------+

    4. Messages rank counter (Redis Hash):

        Key: <project_id>.<queue_name>.rank_counter
    """

    script_names = ['index_messages']

    def __init__(self, *args, **kwargs):
        super(MessageController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection

    @decorators.lazy_property(write=False)
    def _queue_ctrl(self):
        return self.driver.queue_controller

    def _index_messages(self, msgset_key, counter_key, message_ids):
        # NOTE(kgriffs): A watch on a pipe could also be used to ensure
        # messages are inserted in order, but that would be less efficient.
        func = self._scripts['index_messages']

        arguments = [len(message_ids)] + message_ids
        func(keys=[msgset_key, counter_key], args=arguments)

    def _count(self, queue, project):
        """Return total number of messages in a queue.

        Note: Some expired messages may be included in the count if
            they haven't been GC'd yet. This is done for performance.
        """

        return self._client.zcard(utils.msgset_key(queue, project))

    def _create_msgset(self, queue, project, pipe):
        pipe.zadd(MSGSET_INDEX_KEY, 1, utils.msgset_key(queue, project))

    def _delete_msgset(self, queue, project, pipe):
        pipe.zrem(MSGSET_INDEX_KEY, utils.msgset_key(queue, project))

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def _delete_queue_messages(self, queue, project, pipe):
        """Method to remove all the messages belonging to a queue.

        Will be referenced from the QueueController.
        The pipe to execute deletion will be passed from the QueueController
        executing the operation.
        """
        client = self._client
        msgset_key = utils.msgset_key(queue, project)
        message_ids = client.zrange(msgset_key, 0, -1)

        pipe.delete(msgset_key)
        for msg_id in message_ids:
            pipe.delete(msg_id)

    # TODO(prashanthr_): Look for better ways to solve the issue.
    def _find_first_unclaimed(self, queue, project, limit):
        """Find the first unclaimed message in the queue."""

        msgset_key = utils.msgset_key(queue, project)
        now = timeutils.utcnow_ts()

        # TODO(kgriffs): Generalize this paging pattern (DRY)
        offset = 0

        while True:
            msg_keys = self._client.zrange(msgset_key, offset,
                                           offset + limit - 1)
            if not msg_keys:
                return None

            offset += len(msg_keys)

            messages = [MessageEnvelope.from_redis(msg_key, self._client)
                        for msg_key in msg_keys]

            for msg in messages:
                if msg and not utils.msg_claimed_filter(msg, now):
                    return msg.id

    def _exists(self, message_id):
        """Check if message exists in the Queue."""
        return self._client.exists(message_id)

    def _get_first_message_id(self, queue, project, sort):
        """Fetch head/tail of the Queue.

        Helper function to get the first message in the queue
        sort > 0 get from the left else from the right.
        """
        msgset_key = utils.msgset_key(queue, project)

        zrange = self._client.zrange if sort == 1 else self._client.zrevrange
        message_ids = zrange(msgset_key, 0, 0)
        return message_ids[0] if message_ids else None

    def _get_claim(self, message_id):
        """Gets minimal claim doc for a message.

        :returns: {'id': cid, 'expires': ts} IFF the message is claimed,
            and that claim has not expired.
        """

        claim = self._client.hmget(message_id, 'c', 'c.e')

        if claim == [None, None]:
            # NOTE(kgriffs): message_id was not found
            return None

        info = {
            # NOTE(kgriffs): A "None" claim is serialized as an empty str
            'id': encodeutils.safe_decode(claim[0]) or None,
            'expires': int(claim[1]),
        }

        # Is the message claimed?
        now = timeutils.utcnow_ts()
        if info['id'] and (now < info['expires']):
            return info

        # Not claimed
        return None

    def _list(self, queue, project=None, marker=None,
              limit=storage.DEFAULT_MESSAGES_PER_PAGE,
              echo=False, client_uuid=None,
              include_claimed=False,
              to_basic=True):

        if not self._queue_ctrl.exists(queue, project):
            raise errors.QueueDoesNotExist(queue,
                                           project)

        msgset_key = utils.msgset_key(queue, project)
        client = self._client

        if not marker and not include_claimed:
            # NOTE(kgriffs): Skip claimed messages at the head
            # of the queue; otherwise we would just filter them all
            # out and likely end up with an empty list to return.
            marker = self._find_first_unclaimed(queue, project, limit)
            start = client.zrank(msgset_key, marker) or 0
        else:
            rank = client.zrank(msgset_key, marker)
            start = rank + 1 if rank else 0

        message_ids = client.zrange(msgset_key, start,
                                    start + (limit - 1))

        messages = Message.from_redis_bulk(message_ids, client)

        # NOTE(prashanthr_): Build a list of filters for checking
        # the following:
        #
        #     1. Message is expired
        #     2. Message is claimed
        #     3. Message should not be echoed
        #
        now = timeutils.utcnow_ts()
        filters = [functools.partial(utils.msg_expired_filter, now=now)]

        if not include_claimed:
            filters.append(functools.partial(utils.msg_claimed_filter,
                                             now=now))

        if not echo:
            filters.append(functools.partial(utils.msg_echo_filter,
                                             client_uuid=client_uuid))

        marker = {}

        yield _filter_messages(messages, filters, to_basic, marker)
        yield marker['next']

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def gc(self):
        """Garbage-collect expired message data.

        Not all message data can be automatically expired. This method
        cleans up the remainder.

        :returns: Number of messages removed
        """
        claim_ctrl = self.driver.claim_controller
        client = self._client

        num_removed = 0
        offset_msgsets = 0

        while True:
            # NOTE(kgriffs): Iterate across all message sets; there will
            # be one set of message IDs per queue.
            msgset_keys = client.zrange(MSGSET_INDEX_KEY,
                                        offset_msgsets,
                                        offset_msgsets + GC_BATCH_SIZE - 1)
            if not msgset_keys:
                break

            offset_msgsets += len(msgset_keys)

            for msgset_key in msgset_keys:
                msgset_key = encodeutils.safe_decode(msgset_key)

                # NOTE(kgriffs): Drive the claim controller GC from
                # here, because we already know the queue and project
                # scope.
                queue, project = utils.descope_message_ids_set(msgset_key)
                claim_ctrl._gc(queue, project)

                offset_mids = 0

                while True:
                    # NOTE(kgriffs): Look up each message in the message set,
                    # see if it has expired, and if so, remove it from msgset.
                    mids = client.zrange(msgset_key, offset_mids,
                                         offset_mids + GC_BATCH_SIZE - 1)

                    if not mids:
                        break

                    offset_mids += len(mids)

                    # NOTE(kgriffs): If redis expired the message, it will
                    # not exist, so all we have to do is remove mid from
                    # the msgset collection.
                    with client.pipeline() as pipe:
                        for mid in mids:
                            pipe.exists(mid)

                        mid_exists_flags = pipe.execute()

                    with client.pipeline() as pipe:
                        for mid, exists in zip(mids, mid_exists_flags):
                            if not exists:
                                pipe.zrem(msgset_key, mid)
                                num_removed += 1

                        pipe.execute()

        return num_removed

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def list(self, queue, project=None, marker=None,
             limit=storage.DEFAULT_MESSAGES_PER_PAGE,
             echo=False, client_uuid=None,
             include_claimed=False):

        return self._list(queue, project, marker, limit, echo,
                          client_uuid, include_claimed)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def first(self, queue, project=None, sort=1):
        if sort not in (1, -1):
            raise ValueError(u'sort must be either 1 (ascending) '
                             u'or -1 (descending)')

        message_id = self._get_first_message_id(queue, project, sort)
        if not message_id:
            raise errors.QueueIsEmpty(queue, project)

        message = Message.from_redis(message_id, self._client)
        if message is None:
            raise errors.QueueIsEmpty(queue, project)

        now = timeutils.utcnow_ts()
        return message.to_basic(now, include_created=True)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def get(self, queue, message_id, project=None):
        if not self._queue_ctrl.exists(queue, project):
            raise errors.QueueDoesNotExist(queue, project)

        message = Message.from_redis(message_id, self._client)
        now = timeutils.utcnow_ts()

        if message and not utils.msg_expired_filter(message, now):
            return message.to_basic(now)
        else:
            raise errors.MessageDoesNotExist(message_id, queue, project)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def bulk_get(self, queue, message_ids, project=None):
        if not self._queue_ctrl.exists(queue, project):
            return iter([])

        # NOTE(prashanthr_): Pipelining is used here purely
        # for performance.
        with self._client.pipeline() as pipe:
            for mid in message_ids:
                    pipe.hgetall(mid)

            messages = pipe.execute()

        # NOTE(kgriffs): Skip messages that may have been deleted
        now = timeutils.utcnow_ts()
        return (Message.from_hmap(msg).to_basic(now)
                for msg in messages if msg)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def post(self, queue, messages, client_uuid, project=None):
        msgset_key = utils.msgset_key(queue, project)
        counter_key = utils.scope_queue_index(queue, project,
                                              MESSAGE_RANK_COUNTER_SUFFIX)

        message_ids = []
        now = timeutils.utcnow_ts()

        with self._client.pipeline() as pipe:
            for msg in messages:
                prepared_msg = Message(
                    ttl=msg['ttl'],
                    created=now,
                    client_uuid=client_uuid,
                    claim_id=None,
                    claim_expires=now,
                    claim_count=0,
                    body=msg.get('body', {}),
                )

                prepared_msg.to_redis(pipe)
                message_ids.append(prepared_msg.id)

            pipe.execute()

        # NOTE(kgriffs): If this call fails, we will return
        # an error to the client and the messages will be
        # orphaned, but Redis will remove them when they
        # expire, so we will just pretend they don't exist
        # in that case.
        self._index_messages(msgset_key, counter_key, message_ids)

        return message_ids

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def delete(self, queue, message_id, project=None, claim=None):
        claim_ctrl = self.driver.claim_controller
        if not self._queue_ctrl.exists(queue, project):
            return

        # NOTE(kgriffs): The message does not exist, so
        # it is essentially "already" deleted.
        if not self._exists(message_id):
            return

        # TODO(kgriffs): Create decorator for validating claim and message
        # IDs, since those are not checked at the transport layer. This
        # decorator should be applied to all relevant methods.
        if claim is not None:
            try:
                uuid.UUID(claim)
            except ValueError:
                raise errors.ClaimDoesNotExist(claim, queue, project)

        msg_claim = self._get_claim(message_id)
        is_claimed = (msg_claim is not None)

        # Authorize the request based on having the correct claim ID
        if claim is None:
            if is_claimed:
                raise errors.MessageIsClaimed(message_id)

        elif not is_claimed:
            raise errors.MessageNotClaimed(message_id)

        elif msg_claim['id'] != claim:
            if not claim_ctrl._exists(queue, claim, project):
                raise errors.ClaimDoesNotExist(claim, queue, project)

            raise errors.MessageNotClaimedBy(message_id, claim)

        msgset_key = utils.msgset_key(queue, project)

        with self._client.pipeline() as pipe:
            pipe.delete(message_id)
            pipe.zrem(msgset_key, message_id)

            if is_claimed:
                claim_ctrl._del_message(queue, project, msg_claim['id'],
                                        message_id, pipe)

            pipe.execute()

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def bulk_delete(self, queue, message_ids, project=None):
        claim_ctrl = self.driver.claim_controller
        if not self._queue_ctrl.exists(queue, project):
            return

        msgset_key = utils.msgset_key(queue, project)

        with self._client.pipeline() as pipe:
            for mid in message_ids:
                if not self._exists(mid):
                    continue

                pipe.delete(mid)
                pipe.zrem(msgset_key, mid)

                msg_claim = self._get_claim(mid)
                if msg_claim is not None:
                    claim_ctrl._del_message(queue, project, msg_claim['id'],
                                            mid, pipe)
            pipe.execute()

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def pop(self, queue, limit, project=None):
        # Pop is implemented as a chain of the following operations:
        # 1. Create a claim.
        # 2. Delete the messages claimed.
        # 3. Delete the claim.
        claim_ctrl = self.driver.claim_controller
        claim_id, messages = claim_ctrl.create(
            queue, dict(ttl=1, grace=0), project, limit=limit)

        message_ids = [message['id'] for message in messages]
        self.bulk_delete(queue, message_ids, project)
        # NOTE(prashanthr_): Creating a claim controller reference
        # causes a recursive reference. Hence, using the reference
        # from the driver.
        claim_ctrl.delete(queue, claim_id, project)
        return messages


def _filter_messages(messages, filters, to_basic, marker):
    """Create a filtering iterator over a list of messages.

    The function accepts a list of filters to be filtered
    before the the message can be included as a part of the reply.
    """
    now = timeutils.utcnow_ts()

    for msg in messages:
        # NOTE(kgriffs): Message may have been deleted, so
        # check each value to ensure we got a message back
        if msg is None:
            continue

        # NOTE(kgriffs): Check to see if any of the filters
        # indiciate that this message should be skipped.
        for should_skip in filters:
            if should_skip(msg):
                break
        else:
            marker['next'] = msg.id

            if to_basic:
                yield msg.to_basic(now)
            else:
                yield msg

QUEUES_SET_STORE_NAME = 'queues_set'


class MessageQueueHandler(object):
    def __init__(self, driver, control_driver):
        self.driver = driver
        self._client = self.driver.connection
        self._queue_ctrl = self.driver.queue_controller
        self._message_ctrl = self.driver.message_controller
        self._claim_ctrl = self.driver.claim_controller

    @utils.raises_conn_error
    def create(self, name, metadata=None, project=None):
        with self._client.pipeline() as pipe:
            self._message_ctrl._create_msgset(name, project, pipe)

            try:
                pipe.execute()
            except redis.exceptions.ResponseError:
                return False

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def delete(self, name, project=None):
        with self._client.pipeline() as pipe:
            self._message_ctrl._delete_msgset(name, project, pipe)
            self._message_ctrl._delete_queue_messages(name, project, pipe)
            pipe.execute()

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def stats(self, name, project=None):
        if not self._queue_ctrl.exists(name, project=project):
            raise errors.QueueDoesNotExist(name, project)

        total = self._message_ctrl._count(name, project)

        if total:
            claimed = self._claim_ctrl._count_messages(name, project)
        else:
            claimed = 0

        message_stats = {
            'claimed': claimed,
            'free': total - claimed,
            'total': total,
        }

        if total:
            try:
                newest = self._message_ctrl.first(name, project, -1)
                oldest = self._message_ctrl.first(name, project, 1)
            except errors.QueueIsEmpty:
                pass
            else:
                message_stats['newest'] = newest
                message_stats['oldest'] = oldest

        return {'messages': message_stats}

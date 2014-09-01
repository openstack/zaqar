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
import redis

from zaqar.common import decorators
from zaqar.openstack.common import log as logging
from zaqar.openstack.common import timeutils
from zaqar.queues import storage
from zaqar.queues.storage import errors
from zaqar.queues.storage.redis import messages
from zaqar.queues.storage.redis import utils

LOG = logging.getLogger(__name__)

QUEUES_SET_STORE_NAME = 'queues_set'
MESSAGE_IDS_SUFFIX = 'messages'


class QueueController(storage.Queue):
    """Implements queue resource operations using Redis.

    Queues are scoped by project, which is prefixed to the
    queue name.

    Queues (Redis sorted set):

        Key: queues_set

        Id                   Value
        ---------------------------------
        name      ->   <project-id_q-name>


    The set helps faster existence checks, while the list helps
    paginated retrieval of queues.

    Queue Information (Redis hash):

        Key: <project-id_q-name>

        Name                      Field
        -------------------------------
        count                 ->     c
        num_msgs_claimed      ->     cl
        metadata              ->     m
        creation timestamp    ->     t
    """

    def __init__(self, *args, **kwargs):
        super(QueueController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection
        self._packer = msgpack.Packer(encoding='utf-8',
                                      use_bin_type=True).pack
        self._unpacker = functools.partial(msgpack.unpackb, encoding='utf-8')

    @decorators.lazy_property(write=False)
    def _message_ctrl(self):
        return self.driver.message_controller

    def _claim_counter_key(self, name, project):
        return utils.scope_queue_name(name, project)

    def _inc_counter(self, name, project, amount=1, pipe=None):
        queue_key = utils.scope_queue_name(name, project)

        client = pipe if pipe is not None else self._client
        client.hincrby(queue_key, 'c', amount)

    def _inc_claimed(self, name, project, amount=1, pipe=None):
        queue_key = utils.scope_queue_name(name, project)

        client = pipe if pipe is not None else self._client
        client.hincrby(queue_key, 'cl', amount)

    # TODO(kgriffs): Reimplement in Lua; this is way too expensive!
    def _get_expired_message_count(self, name, project):
        """Calculate the number of expired messages in the queue.

        Used to compute the stats on the queue.
        Method has O(n) complexity as we iterate the entire list of
        messages.
        """

        messages_set_key = utils.scope_message_ids_set(name, project,
                                                       MESSAGE_IDS_SUFFIX)

        with self._client.pipeline() as pipe:
            for msg_key in self._client.zrange(messages_set_key, 0, -1):
                pipe.hgetall(msg_key)

            raw_messages = pipe.execute()

        expired = 0
        now = timeutils.utcnow_ts()

        for msg in raw_messages:
            if msg:
                msg = messages.Message.from_redis(msg)
                if utils.msg_expired_filter(msg, now):
                    expired += 1

        return expired

    def _get_queue_info(self, queue_key, fields, transform=str):
        """Get one or more fields from Queue Info."""

        values = self._client.hmget(queue_key, fields)
        return [transform(v) for v in values] if transform else values

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def list(self, project=None, marker=None,
             limit=storage.DEFAULT_QUEUES_PER_PAGE, detailed=False):
        client = self._client
        qset_key = utils.scope_queue_name(QUEUES_SET_STORE_NAME, project)
        marker = utils.scope_queue_name(marker, project)
        rank = client.zrank(qset_key, marker)
        start = rank + 1 if rank else 0

        cursor = (q for q in client.zrange(qset_key, start,
                                           start + limit - 1))
        marker_next = {}

        def denormalizer(info, name):
            queue = {'name': utils.descope_queue_name(name)}
            marker_next['next'] = queue['name']
            if detailed:
                queue['metadata'] = info[1]

            return queue

        yield utils.QueueListCursor(self._client, cursor, denormalizer)
        yield marker_next and marker_next['next']

    def get(self, name, project=None):
        """Obtain the metadata from the queue."""
        return self.get_metadata(name, project)

    @utils.raises_conn_error
    def create(self, name, metadata=None, project=None):
        # TODO(prashanthr_): Implement as a lua script.
        queue_key = utils.scope_queue_name(name, project)
        qset_key = utils.scope_queue_name(QUEUES_SET_STORE_NAME, project)

        # Check if the queue already exists.
        if self.exists(name, project):
            return False

        queue = {
            'c': 0,
            'cl': 0,
            'm': self._packer(metadata or {}),
            't': timeutils.utcnow_ts()
        }

        # Pipeline ensures atomic inserts.
        with self._client.pipeline() as pipe:
            pipe.zadd(qset_key, 1, queue_key).hmset(queue_key, queue)

            try:
                pipe.execute()
            except redis.exceptions.ResponseError:
                return False

        return True

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def exists(self, name, project=None):
        # TODO(prashanthr_): Cache this lookup
        queue_key = utils.scope_queue_name(name, project)
        qset_key = utils.scope_queue_name(QUEUES_SET_STORE_NAME, project)

        return self._client.zrank(qset_key, queue_key) is not None

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def set_metadata(self, name, metadata, project=None):
        if not self.exists(name, project):
            raise errors.QueueDoesNotExist(name, project)

        key = utils.scope_queue_name(name, project)
        fields = {'m': self._packer(metadata)}

        self._client.hmset(key, fields)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def get_metadata(self, name, project=None):
        if not self.exists(name, project):
            raise errors.QueueDoesNotExist(name, project)

        queue_key = utils.scope_queue_name(name, project)
        metadata = self._get_queue_info(queue_key, b'm', None)[0]

        return self._unpacker(metadata)

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def delete(self, name, project=None):
        queue_key = utils.scope_queue_name(name, project)
        qset_key = utils.scope_queue_name(QUEUES_SET_STORE_NAME, project)

        # NOTE(prashanthr_): Pipelining is used to mitigate race conditions
        with self._client.pipeline() as pipe:
            pipe.zrem(qset_key, queue_key)
            pipe.delete(queue_key)
            self._message_ctrl._delete_queue_messages(name, project, pipe)

            pipe.execute()

    @utils.raises_conn_error
    @utils.retries_on_connection_error
    def stats(self, name, project=None):
        if not self.exists(name, project=project):
            raise errors.QueueDoesNotExist(name, project)

        queue_key = utils.scope_queue_name(name, project)

        claimed, total = self._get_queue_info(queue_key, [b'cl', b'c'], int)
        expired = self._get_expired_message_count(name, project)

        message_stats = {
            'claimed': claimed,
            'free': total - claimed - expired,
            'total': total
        }

        try:
            newest = self._message_ctrl.first(name, project, -1)
            oldest = self._message_ctrl.first(name, project, 1)
        except errors.QueueIsEmpty:
            pass
        else:
            message_stats['newest'] = newest
            message_stats['oldest'] = oldest

        return {'messages': message_stats}

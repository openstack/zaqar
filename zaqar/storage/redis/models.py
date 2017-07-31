# Copyright (c) 2014 Prashanth Raghu.
# Copyright (c) 2015 Catalyst IT Ltd.
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

import functools
import uuid

import msgpack
from oslo_utils import encodeutils
from oslo_utils import timeutils
from oslo_utils import uuidutils

MSGENV_FIELD_KEYS = (b'id', b't', b'cr', b'e', b'u', b'c', b'c.e', b'c.c')
SUBENV_FIELD_KEYS = (b'id', b's', b'u', b't', b'e', b'o', b'p', b'c')


# TODO(kgriffs): Make similar classes for claims and queues
class MessageEnvelope(object):
    """Encapsulates the message envelope (metadata only, no body).

    :param id: Message ID in the form of a hexadecimal UUID. If not
        given, one will be automatically generated.
    :param ttl: Message TTL in seconds
    :param created: Message creation time as a UNIX timestamp
    :param client_uuid: UUID of the client that posted the message
    :param claim_id: If claimed, the UUID of the claim. Set to None
        for messages that have never been claimed.
    :param claim_expires: Claim expiration as a UNIX timestamp
    """

    __slots__ = [
        'id',
        'ttl',
        'created',
        'expires',
        'client_uuid',
        'claim_id',
        'claim_expires',
        'claim_count',
    ]

    def __init__(self, **kwargs):
        self.id = _validate_uuid4(kwargs.get('id', uuidutils.generate_uuid()))
        self.ttl = kwargs['ttl']
        self.created = kwargs['created']
        self.expires = kwargs.get('expires', self.created + self.ttl)

        self.client_uuid = _validate_uuid4(str(kwargs['client_uuid']))

        self.claim_id = kwargs.get('claim_id')
        if self.claim_id:
            _validate_uuid4(self.claim_id)
        self.claim_expires = kwargs['claim_expires']
        self.claim_count = kwargs.get('claim_count', 0)

    @staticmethod
    def from_hmap(hmap):
        kwargs = _hmap_to_msgenv_kwargs(hmap)
        return MessageEnvelope(**kwargs)

    @staticmethod
    def from_redis(mid, client):
        values = client.hmget(mid, MSGENV_FIELD_KEYS)

        # NOTE(kgriffs): If the key does not exist, redis-py returns
        # an array of None values.
        if values[0] is None:
            return None

        return _hmap_kv_to_msgenv(MSGENV_FIELD_KEYS, values)

    @staticmethod
    def from_redis_bulk(message_ids, client):
        with client.pipeline() as pipe:
            for mid in message_ids:
                pipe.hmget(mid, MSGENV_FIELD_KEYS)

            results = pipe.execute()

        message_envs = []
        for value_list in results:
            if value_list is None:
                env = None
            else:
                env = _hmap_kv_to_msgenv(MSGENV_FIELD_KEYS, value_list)

            message_envs.append(env)

        return message_envs

    def to_redis(self, pipe):
        hmap = _msgenv_to_hmap(self)

        pipe.hmset(self.id, hmap)
        pipe.expire(self.id, self.ttl)


class SubscriptionEnvelope(object):
    """Encapsulates the subscription envelope."""

    __slots__ = [
        'id',
        'source',
        'subscriber',
        'ttl',
        'expires',
        'options',
        'project',
        'confirmed',
    ]

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuidutils.generate_uuid())
        self.source = kwargs['source']
        self.subscriber = kwargs['subscriber']
        self.ttl = kwargs['ttl']
        self.expires = kwargs.get('expires', float('inf'))
        self.options = kwargs['options']
        self.confirmed = kwargs.get('confirmed', 'True')

    @staticmethod
    def from_redis(sid, client):
        values = client.hmget(sid, SUBENV_FIELD_KEYS)

        # NOTE(kgriffs): If the key does not exist, redis-py returns
        # an array of None values.
        if values[0] is None:
            return None

        return _hmap_kv_to_subenv(SUBENV_FIELD_KEYS, values)

    def to_redis(self, pipe):
        hmap = _subenv_to_hmap(self)

        pipe.hmset(self.id, hmap)
        pipe.expire(self.id, self.ttl)

    def to_basic(self, now):
        created = self.expires - self.ttl
        is_confirmed = self.confirmed == str(True)
        basic_msg = {
            'id': self.id,
            'source': self.source,
            'subscriber': self.subscriber,
            'ttl': self.ttl,
            'age': now - created,
            'options': self.options,
            'confirmed': is_confirmed,
        }

        return basic_msg


# NOTE(kgriffs): This could have implemented MessageEnvelope functionality
# by adding an "include_body" param to all the methods, but then you end
# up with tons of if statements that make the code rather ugly.
class Message(MessageEnvelope):
    """Represents an entire message, including envelope and body.

    :param id: Message ID in the form of a hexadecimal UUID. If not
        given, one will be automatically generated.
    :param ttl: Message TTL in seconds
    :param created: Message creation time as a UNIX timestamp
    :param client_uuid: UUID of the client that posted the message
    :param claim_id: If claimed, the UUID of the claim. Set to None
        for messages that have never been claimed.
    :param claim_expires: Claim expiration as a UNIX timestamp
    :param body: Message payload. Must be serializable to mspack.
    """

    __slots__ = MessageEnvelope.__slots__ + ['body']

    def __init__(self, **kwargs):
        super(Message, self).__init__(**kwargs)
        self.body = kwargs['body']

    @staticmethod
    def from_hmap(hmap):
        kwargs = _hmap_to_msgenv_kwargs(hmap)
        kwargs['body'] = _unpack(hmap[b'b'])

        return Message(**kwargs)

    @staticmethod
    def from_redis(mid, client):
        hmap = client.hgetall(mid)
        return Message.from_hmap(hmap) if hmap else None

    @staticmethod
    def from_redis_bulk(message_ids, client):
        with client.pipeline() as pipe:
            for mid in message_ids:
                pipe.hgetall(mid)

            results = pipe.execute()

        messages = [Message.from_hmap(hmap) if hmap else None
                    for hmap in results]

        return messages

    def to_redis(self, pipe, include_body=True):
        if not include_body:
            super(Message, self).to_redis(pipe)

        hmap = _msgenv_to_hmap(self)
        hmap['b'] = _pack(self.body)

        pipe.hmset(self.id, hmap)
        pipe.expire(self.id, self.ttl)

    def to_basic(self, now, include_created=False):
        basic_msg = {
            'id': self.id,
            'age': now - self.created,
            'ttl': self.ttl,
            'body': self.body,
            'claim_id': self.claim_id,
            'claim_count': self.claim_count,
        }

        if include_created:
            created_iso = timeutils.iso8601_from_timestamp(self.created)
            basic_msg['created'] = created_iso

        return basic_msg


# ==========================================================================
# Helpers
# ==========================================================================


_pack = msgpack.Packer(encoding='utf-8', use_bin_type=True).pack
_unpack = functools.partial(msgpack.unpackb, encoding='utf-8')


def _hmap_kv_to_msgenv(keys, values):
    hmap = dict(zip(keys, values))
    kwargs = _hmap_to_msgenv_kwargs(hmap)
    return MessageEnvelope(**kwargs)


def _hmap_to_msgenv_kwargs(hmap):
    claim_id = hmap[b'c']
    if claim_id:
        claim_id = encodeutils.safe_decode(claim_id)
    else:
        claim_id = None

    # NOTE(kgriffs): Under Py3K, redis-py converts all strings
    # into binary. Woohoo!
    return {
        'id': encodeutils.safe_decode(hmap[b'id']),
        'ttl': int(hmap[b't']),
        'created': int(hmap[b'cr']),
        'expires': int(hmap[b'e']),

        'client_uuid': encodeutils.safe_decode(hmap[b'u']),

        'claim_id': claim_id,
        'claim_expires': int(hmap[b'c.e']),
        'claim_count': int(hmap[b'c.c']),
    }


def _msgenv_to_hmap(msg):
    return {
        'id': msg.id,
        't': msg.ttl,
        'cr': msg.created,
        'e': msg.expires,
        'u': msg.client_uuid,
        'c': msg.claim_id or '',
        'c.e': msg.claim_expires,
        'c.c': msg.claim_count,
    }


def _hmap_kv_to_subenv(keys, values):
    hmap = dict(zip(keys, values))
    kwargs = _hmap_to_subenv_kwargs(hmap)
    return SubscriptionEnvelope(**kwargs)


def _hmap_to_subenv_kwargs(hmap):
    # NOTE(kgriffs): Under Py3K, redis-py converts all strings
    # into binary. Woohoo!
    return {
        'id': encodeutils.safe_decode(hmap[b'id']),
        'source': hmap[b's'],
        'subscriber': hmap[b'u'],
        'ttl': int(hmap[b't']),
        'expires': int(hmap[b'e']),
        'options': _unpack(hmap[b'o']),
        'confirmed': hmap[b'c']
    }


def _subenv_to_hmap(msg):
    return {
        'id': msg.id,
        's': msg.source,
        'u': msg.subscriber,
        't': msg.ttl,
        'e': msg.expires,
        'o': msg.options
    }


def _validate_uuid4(_uuid):
    uuid.UUID(str(_uuid), version=4)
    return _uuid

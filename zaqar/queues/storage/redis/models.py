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

import msgpack

from zaqar.openstack.common import strutils
from zaqar.openstack.common import timeutils


_pack = msgpack.Packer(encoding='utf-8', use_bin_type=True).pack
_unpack = functools.partial(msgpack.unpackb, encoding='utf-8')


# TODO(kgriffs): Make similar classes for claims and queues
class Message(object):
    """Message is used to organize,store and retrieve messages from redis.

    Message class helps organize,store and retrieve messages in a version
    compatible manner.

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
    message_data = {}

    __slots__ = (
        'id',
        'ttl',
        'created',
        'expires',
        'client_uuid',
        'claim_id',
        'claim_expires',
        'body',
    )

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.ttl = kwargs['ttl']
        self.created = kwargs['created']
        self.expires = kwargs.get('expires', self.created + self.ttl)

        self.client_uuid = str(kwargs['client_uuid'])

        self.claim_id = kwargs.get('claim_id')
        self.claim_expires = kwargs['claim_expires']

        self.body = kwargs['body']

    @property
    def created_iso(self):
        return timeutils.iso8601_from_timestamp(self.created)

    @staticmethod
    def from_redis(doc):
        claim_id = doc[b'c']
        if claim_id:
            claim_id = strutils.safe_decode(claim_id)
        else:
            claim_id = None

        # NOTE(kgriffs): Under Py3K, redis-py converts all strings
        # into binary. Woohoo!
        return Message(
            id=strutils.safe_decode(doc[b'id']),
            ttl=int(doc[b't']),
            created=int(doc[b'cr']),
            expires=int(doc[b'e']),

            client_uuid=strutils.safe_decode(doc[b'u']),

            claim_id=claim_id,
            claim_expires=int(doc[b'c.e']),

            body=_unpack(doc[b'b']),
        )

    def to_redis(self, pipe):
        doc = {
            'id': self.id,
            't': self.ttl,
            'cr': self.created,
            'e': self.expires,
            'u': self.client_uuid,
            'c': self.claim_id or '',
            'c.e': self.claim_expires,
            'b': _pack(self.body),
        }

        pipe.hmset(self.id, doc)

    def to_basic(self, now, include_created=False):
        basic_msg = {
            'id': self.id,
            'age': now - self.created,
            'ttl': self.ttl,
            'body': self.body
        }

        if include_created:
            basic_msg['created'] = self.created_iso

        return basic_msg

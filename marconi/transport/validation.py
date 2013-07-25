# Copyright (c) 2013 Rackspace, Inc.
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

import re

import simplejson as json

from marconi.common import config
from marconi.common import exceptions

OPTIONS = {
    'queue_payload_uplimit': 20,
    'message_payload_uplimit': 20,
    'message_size_uplimit': 256 * 1024,
    'message_ttl_max': 1209600,
    'claim_ttl_max': 43200,
    'claim_grace_max': 43200,
}

CFG = config.namespace('limits:transport').from_options(**OPTIONS)

QUEUE_NAME_REGEX = re.compile('^[\w-]+$')


def queue_creation(name):
    """Restrictions on a queue name.

    :param name: The queue name
    :raises: ValidationFailed if the name is longer than 64 bytes or
        contains bytes other than ASCII digits, letters, underscore,
        and dash.
    """

    if len(name) > 64:
        raise exceptions.ValidationFailed(
            'queue name longer than 64 bytes')

    if not QUEUE_NAME_REGEX.match(name):
        raise exceptions.ValidationFailed(
            'queue name contains forbidden characters')


def queue_listing(limit=None, **kwargs):
    """Restrictions involving a list of queues.

    :param limit: The expected number of queues in the list
    :param kwargs: Ignored arguments passed to storage API
    :raises: ValidationFailed if the limit is exceeded
    """

    if limit is not None and not (0 < limit <= CFG.queue_payload_uplimit):
        raise exceptions.ValidationFailed(
            'queue payload count not in (0, %d]' %
            CFG.queue_payload_uplimit)


def message_posting(messages, check_size=True):
    """Restrictions on a list of messages.

    :param messages: A list of messages
    :param check_size: Whether the size checking for each message
        is required
    :raises: ValidationFailed if any message has a out-of-range
        TTL, or an oversize message body.
    """

    message_listing(limit=len(messages))

    for msg in messages:
        message_content(msg, check_size)


def message_content(message, check_size):
    """Restrictions on each message."""

    if not (60 <= message['ttl'] <= CFG.message_ttl_max):
        raise exceptions.ValidationFailed(
            'message TTL not in [60, %d]' %
            CFG.message_ttl_max)

    if check_size:
        # UTF-8 encoded, without whitespace
        # TODO(zyuan): Replace this redundent re-serialization
        # with a sizing-only parser.
        body_length = len(json.dumps(message['body'],
                                     ensure_ascii=False,
                                     separators=(',', ':')))
        if body_length > CFG.message_size_uplimit:
            raise exceptions.ValidationFailed(
                'message body larger than %d bytes' %
                CFG.message_size_uplimit)


def message_listing(limit=None, **kwargs):
    """Restrictions involving a list of messages.

    :param limit: The expected number of messages in the list
    :param kwargs: Ignored arguments passed to storage API
    :raises: ValidationFailed if the limit is exceeded
    """

    if limit is not None and not (0 < limit <= CFG.message_payload_uplimit):
        raise exceptions.ValidationFailed(
            'message payload count not in (0, %d]' %
            CFG.message_payload_uplimit)


def claim_creation(metadata, **kwargs):
    """Restrictions on the claim parameters upon creation.

    :param metadata: The claim metadata
    :param kwargs: Other arguments passed to storage API
    :raises: ValidationFailed if either TTL or grace is out of range,
        or the expected number of messages exceed the limit.
    """

    message_listing(**kwargs)
    claim_updating(metadata)

    if not (60 <= metadata['grace'] <= CFG.claim_grace_max):
        raise exceptions.ValidationFailed(
            'claim grace not in [60, %d]' %
            CFG.claim_grace_max)


def claim_updating(metadata):
    """Restrictions on the claim TTL.

    :param metadata: The claim metadata
    :param kwargs: Ignored arguments passed to storage API
    :raises: ValidationFailed if the TTL is out of range
    """

    if not (60 <= metadata['ttl'] <= CFG.claim_ttl_max):
        raise exceptions.ValidationFailed(
            'claim TTL not in [60, %d]' %
            CFG.claim_ttl_max)

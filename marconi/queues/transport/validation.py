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

OPTIONS = {
    'queue_paging_uplimit': 20,
    'metadata_size_uplimit': 64 * 1024,
    'message_paging_uplimit': 20,
    'message_size_uplimit': 256 * 1024,
    'message_ttl_max': 1209600,
    'claim_ttl_max': 43200,
    'claim_grace_max': 43200,
}

CFG = config.namespace('queues:limits:transport').from_options(**OPTIONS)

# NOTE(kgriffs): Don't use \w because it isn't guaranteed to match
# only ASCII characters.
QUEUE_NAME_REGEX = re.compile('^[a-zA-Z0-9_\-]+$')
QUEUE_NAME_MAX_LEN = 64


class ValidationFailed(ValueError):
    """User input did not follow API restrictions."""


def queue_name(name):
    """Restrictions on a queue name.

    :param name: The queue name
    :raises: ValidationFailed if the name is longer than 64 bytes or
        contains anything other than ASCII digits and letters,
        underscores, and dashes.
    """

    if len(name) > QUEUE_NAME_MAX_LEN:
        raise ValidationFailed(
            'Queue names may not be more than 64 characters long.')

    if not QUEUE_NAME_REGEX.match(name):
        raise ValidationFailed(
            'Queue names may only contain ASCII letters, digits, '
            'underscores, and dashes.')


def queue_listing(limit=None, **kwargs):
    """Restrictions involving a list of queues.

    :param limit: The expected number of queues in the list
    :param kwargs: Ignored arguments passed to storage API
    :raises: ValidationFailed if the limit is exceeded
    """

    if limit is not None and not (0 < limit <= CFG.queue_paging_uplimit):
        raise ValidationFailed(
            'Limit must be at least 1 and no greater than %d.' %
            CFG.queue_paging_uplimit)


def queue_content(metadata, check_size):
    """Restrictions on queue metadata.

    :param metadata: Metadata as a Python dict
    :param check_size: Whether this size checking is required
    :raises: ValidationFailed if the metadata is oversize.
    """

    if check_size:
        length = _compact_json_length(metadata)
        if length > CFG.metadata_size_uplimit:
            raise ValidationFailed(
                ('Queue metadata may not exceed %d characters, '
                 'excluding whitespace.') %
                CFG.metadata_size_uplimit)


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
        raise ValidationFailed(
            ('The TTL for a message may not exceed %d seconds, and '
             'must be at least 60 seconds long.') %
            CFG.message_ttl_max)

    if check_size:
        body_length = _compact_json_length(message['body'])
        if body_length > CFG.message_size_uplimit:
            raise ValidationFailed(
                ('Message bodies may not exceed %d characters, '
                 'excluding whitespace.') %
                CFG.message_size_uplimit)


def message_listing(limit=None, **kwargs):
    """Restrictions involving a list of messages.

    :param limit: The expected number of messages in the list
    :param kwargs: Ignored arguments passed to storage API
    :raises: ValidationFailed if the limit is exceeded
    """

    if limit is not None and not (0 < limit <= CFG.message_paging_uplimit):
        raise ValidationFailed(
            'Limit must be at least 1 and may not be greater than %d. ' %
            CFG.message_paging_uplimit)


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
        raise ValidationFailed(
            ('Grace must be at least 60 seconds and cannot '
             'exceed %d.') %
            CFG.claim_grace_max)


def claim_updating(metadata):
    """Restrictions on the claim TTL.

    :param metadata: The claim metadata
    :param kwargs: Ignored arguments passed to storage API
    :raises: ValidationFailed if the TTL is out of range
    """

    if not (60 <= metadata['ttl'] <= CFG.claim_ttl_max):
        raise ValidationFailed(
            ('The TTL for a claim may not exceed %d seconds, and must be '
             'at least 60 seconds long.') %
            CFG.claim_ttl_max)


def _compact_json_length(obj):
    # UTF-8 encoded, without whitespace
    # TODO(zyuan): Replace this redundent re-serialization
    # with a sizing-only parser.
    return len(json.dumps(obj,
                          ensure_ascii=False,
                          separators=(',', ':')))

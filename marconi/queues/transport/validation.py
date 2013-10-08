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

import json
import re

from oslo.config import cfg


_TRANSPORT_LIMITS_OPTIONS = [
    cfg.IntOpt('queue_paging_uplimit', default=20),
    cfg.IntOpt('metadata_size_uplimit', default=64 * 1024),
    cfg.IntOpt('message_paging_uplimit', default=20),
    cfg.IntOpt('message_size_uplimit', default=256 * 1024),
    cfg.IntOpt('message_ttl_max', default=1209600),
    cfg.IntOpt('claim_ttl_max', default=43200),
    cfg.IntOpt('claim_grace_max', default=43200),
]

_TRANSPORT_LIMITS_GROUP = 'limits:transport'

# NOTE(kgriffs): Don't use \w because it isn't guaranteed to match
# only ASCII characters.
QUEUE_NAME_REGEX = re.compile('^[a-zA-Z0-9_\-]+$')
QUEUE_NAME_MAX_LEN = 64
PROJECT_ID_MAX_LEN = 256


class ValidationFailed(ValueError):
    """User input did not follow API restrictions."""


class Validator(object):
    def __init__(self, conf):
        self._conf = conf
        self._conf.register_opts(_TRANSPORT_LIMITS_OPTIONS,
                                 group=_TRANSPORT_LIMITS_GROUP)
        self._limits_conf = self._conf[_TRANSPORT_LIMITS_GROUP]

    def queue_identification(self, queue, project):
        """Restrictions on a project id & queue name pair.

        :param queue: Name of the queue
        :param project: Project id
        :raises: ValidationFailed if the `name` is longer than 64
            characters or contains anything other than ASCII digits and
            letters, underscores, and dashes.  Also raises if `project`
            is not None but longer than 256 characters.
        """

        if project is not None and len(project) > PROJECT_ID_MAX_LEN:
            raise ValidationFailed(
                'Project ids may not be more than %d characters long.'
                % PROJECT_ID_MAX_LEN)

        if len(queue) > QUEUE_NAME_MAX_LEN:
            raise ValidationFailed(
                'Queue names may not be more than %d characters long.'
                % QUEUE_NAME_MAX_LEN)

        if not QUEUE_NAME_REGEX.match(queue):
            raise ValidationFailed(
                'Queue names may only contain ASCII letters, digits, '
                'underscores, and dashes.')

    def queue_listing(self, limit=None, **kwargs):
        """Restrictions involving a list of queues.

        :param limit: The expected number of queues in the list
        :param kwargs: Ignored arguments passed to storage API
        :raises: ValidationFailed if the limit is exceeded
        """

        uplimit = self._limits_conf.queue_paging_uplimit
        if limit is not None and not (0 < limit <= uplimit):
            raise ValidationFailed(
                'Limit must be at least 1 and no greater than %d.' %
                self._limits_conf.queue_paging_uplimit)

    def queue_content(self, metadata, check_size):
        """Restrictions on queue metadata.

        :param metadata: Metadata as a Python dict
        :param check_size: Whether this size checking is required
        :raises: ValidationFailed if the metadata is oversize.
        """

        if check_size:
            length = _compact_json_length(metadata)
            if length > self._limits_conf.metadata_size_uplimit:
                raise ValidationFailed(
                    ('Queue metadata may not exceed %d characters, '
                     'excluding whitespace.') %
                    self._limits_conf.metadata_size_uplimit)

    def message_posting(self, messages, check_size=True):
        """Restrictions on a list of messages.

        :param messages: A list of messages
        :param check_size: Whether the size checking for each message
            is required
        :raises: ValidationFailed if any message has a out-of-range
            TTL, or an oversize message body.
        """

        self.message_listing(limit=len(messages))

        for msg in messages:
            self.message_content(msg, check_size)

    def message_content(self, message, check_size):
        """Restrictions on each message."""

        if not (60 <= message['ttl'] <= self._limits_conf.message_ttl_max):
            raise ValidationFailed(
                ('The TTL for a message may not exceed %d seconds, and '
                 'must be at least 60 seconds long.') %
                self._limits_conf.message_ttl_max)

        if check_size:
            body_length = _compact_json_length(message['body'])
            if body_length > self._limits_conf.message_size_uplimit:
                raise ValidationFailed(
                    ('Message bodies may not exceed %d characters, '
                     'excluding whitespace.') %
                    self._limits_conf.message_size_uplimit)

    def message_listing(self, limit=None, **kwargs):
        """Restrictions involving a list of messages.

        :param limit: The expected number of messages in the list
        :param kwargs: Ignored arguments passed to storage API
        :raises: ValidationFailed if the limit is exceeded
        """

        uplimit = self._limits_conf.message_paging_uplimit
        if limit is not None and not (0 < limit <= uplimit):
            raise ValidationFailed(
                'Limit must be at least 1 and may not be greater than %d. ' %
                self._limits_conf.message_paging_uplimit)

    def claim_creation(self, metadata, **kwargs):
        """Restrictions on the claim parameters upon creation.

        :param metadata: The claim metadata
        :param kwargs: Other arguments passed to storage API
        :raises: ValidationFailed if either TTL or grace is out of range,
            or the expected number of messages exceed the limit.
        """

        self.message_listing(**kwargs)
        self.claim_updating(metadata)

        if not (60 <= metadata['grace'] <= self._limits_conf.claim_grace_max):
            raise ValidationFailed(
                ('Grace must be at least 60 seconds and cannot '
                 'exceed %d.') %
                self._limits_conf.claim_grace_max)

    def claim_updating(self, metadata):
        """Restrictions on the claim TTL.

        :param metadata: The claim metadata
        :param kwargs: Ignored arguments passed to storage API
        :raises: ValidationFailed if the TTL is out of range
        """

        if not (60 <= metadata['ttl'] <= self._limits_conf.claim_ttl_max):
            raise ValidationFailed(
                ('The TTL for a claim may not exceed %d seconds, and must be '
                 'at least 60 seconds long.') %
                self._limits_conf.claim_ttl_max)


def _compact_json_length(obj):
    # UTF-8 encoded, without whitespace
    # TODO(zyuan): Replace this redundent re-serialization
    # with a sizing-only parser.
    return len(json.dumps(obj,
                          ensure_ascii=False,
                          separators=(',', ':')))

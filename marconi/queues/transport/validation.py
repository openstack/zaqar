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

from oslo.config import cfg

from marconi.i18n import _

MIN_MESSAGE_TTL = 60
MIN_CLAIM_TTL = 60
MIN_CLAIM_GRACE = 60

_TRANSPORT_LIMITS_OPTIONS = (
    cfg.IntOpt('max_queues_per_page', default=20,
               deprecated_name='queue_paging_uplimit',
               deprecated_group='limits:transport'),
    cfg.IntOpt('max_messages_per_page', default=20,
               deprecated_name='message_paging_uplimit',
               deprecated_group='limits:transport'),

    cfg.IntOpt('max_messages_per_claim_or_pop', default=20,
               deprecated_name='max_messages_per_claim',
               help='The maximum number of messages that can be claimed (OR) '
                    'popped in a single request'),

    cfg.IntOpt('max_queue_metadata', default=64 * 1024,
               deprecated_name='metadata_size_uplimit',
               deprecated_group='limits:transport'),
    cfg.IntOpt('max_message_size', default=256 * 1024,
               deprecated_name='message_size_uplimit',
               deprecated_group='limits:transport'),

    cfg.IntOpt('max_message_ttl', default=1209600,
               deprecated_name='message_ttl_max',
               deprecated_group='limits:transport'),
    cfg.IntOpt('max_claim_ttl', default=43200,
               deprecated_name='claim_ttl_max',
               deprecated_group='limits:transport'),
    cfg.IntOpt('max_claim_grace', default=43200,
               deprecated_name='claim_grace_max',
               deprecated_group='limits:transport'),
)

_TRANSPORT_LIMITS_GROUP = 'transport'

# NOTE(kgriffs): Don't use \w because it isn't guaranteed to match
# only ASCII characters.
QUEUE_NAME_REGEX = re.compile('^[a-zA-Z0-9_\-]+$')
QUEUE_NAME_MAX_LEN = 64
PROJECT_ID_MAX_LEN = 256


def _config_options():
    return [(_TRANSPORT_LIMITS_GROUP, _TRANSPORT_LIMITS_OPTIONS)]


class ValidationFailed(ValueError):
    """User input did not follow API restrictions."""

    def __init__(self, msg, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        super(ValidationFailed, self).__init__(msg)


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
            msg = _(u'Project ids may not be more than {0} characters long.')
            raise ValidationFailed(msg, PROJECT_ID_MAX_LEN)

        if len(queue) > QUEUE_NAME_MAX_LEN:
            msg = _(u'Queue names may not be more than {0} characters long.')
            raise ValidationFailed(msg, QUEUE_NAME_MAX_LEN)

        if not QUEUE_NAME_REGEX.match(queue):
            raise ValidationFailed(
                _(u'Queue names may only contain ASCII letters, digits, '
                  'underscores, and dashes.'))

    def queue_listing(self, limit=None, **kwargs):
        """Restrictions involving a list of queues.

        :param limit: The expected number of queues in the list
        :param kwargs: Ignored arguments passed to storage API
        :raises: ValidationFailed if the limit is exceeded
        """

        uplimit = self._limits_conf.max_queues_per_page
        if limit is not None and not (0 < limit <= uplimit):
            msg = _(u'Limit must be at least 1 and no greater than {0}.')
            raise ValidationFailed(msg, self._limits_conf.max_queues_per_page)

    def queue_metadata_length(self, content_length):
        """Restrictions on queue's length.

        :param content_length: Queue request's length.
        :raises: ValidationFailed if the metadata is oversize.
        """
        if content_length is None:
            return
        if content_length > self._limits_conf.max_queue_metadata:
            msg = _(u'Queue metadata is too large. Max size: {0}')
            raise ValidationFailed(msg, self._limits_conf.max_queue_metadata)

    def message_posting(self, messages):
        """Restrictions on a list of messages.

        :param messages: A list of messages
        :raises: ValidationFailed if any message has a out-of-range
            TTL.
        """

        if not messages:
            raise ValidationFailed(_(u'No messages to enqueu.'))

        for msg in messages:
            self.message_content(msg)

    def message_length(self, content_length):
        """Restrictions on message post length.

        :param content_length: Queue request's length.
        :raises: ValidationFailed if the metadata is oversize.
        """
        if content_length is None:
            return
        if content_length > self._limits_conf.max_message_size:
            raise ValidationFailed(
                _(u'Message collection size is too large. Max size {0}'),
                self._limits_conf.max_message_size)

    def message_content(self, message):
        """Restrictions on each message."""

        ttl = message['ttl']

        if not (MIN_MESSAGE_TTL <= ttl <= self._limits_conf.max_message_ttl):
            msg = _(u'The TTL for a message may not exceed {0} seconds, and '
                    'must be at least {1} seconds long.')

            raise ValidationFailed(
                msg, self._limits_conf.max_message_ttl, MIN_MESSAGE_TTL)

    def message_listing(self, limit=None, **kwargs):
        """Restrictions involving a list of messages.

        :param limit: The expected number of messages in the list
        :param kwargs: Ignored arguments passed to storage API
        :raises: ValidationFailed if the limit is exceeded
        """

        uplimit = self._limits_conf.max_messages_per_page
        if limit is not None and not (0 < limit <= uplimit):
            msg = _(u'Limit must be at least 1 and may not '
                    'be greater than {0}.')

            raise ValidationFailed(
                msg, self._limits_conf.max_messages_per_page)

    def message_deletion(self, ids=None, pop=None):
        """Restrictions involving deletion of messages.

        :param ids: message ids passed in by the delete request
        :param pop: count of messages to be POPped
        :raises: ValidationFailed if,
                 pop AND id params are present together
                 neither pop or id params are present
                 message count to be popped > maximum allowed
        """

        if pop is not None and ids is not None:
            msg = _(u'pop and id params cannot be present together in the '
                    'delete request.')

            raise ValidationFailed(msg)

        if pop is None and ids is None:
            msg = _(u'The request should have either "ids" or "pop" '
                    'parameter in the request, to be able to delete.')

            raise ValidationFailed(msg)

        pop_uplimit = self._limits_conf.max_messages_per_claim_or_pop
        if pop is not None and not (0 < pop <= pop_uplimit):
            msg = _(u'Pop value must be at least 1 and may not '
                    'be greater than {0}.')

            raise ValidationFailed(msg, pop_uplimit)

        delete_uplimit = self._limits_conf.max_messages_per_page
        if ids is not None and not (0 < len(ids) <= delete_uplimit):
            msg = _(u'ids parameter should have at least 1 and not '
                    'greater than {0} values.')

            raise ValidationFailed(msg, delete_uplimit)

    def claim_creation(self, metadata, limit=None):
        """Restrictions on the claim parameters upon creation.

        :param metadata: The claim metadata
        :param limit: The number of messages to claim
        :raises: ValidationFailed if either TTL or grace is out of range,
            or the expected number of messages exceed the limit.
        """

        self.claim_updating(metadata)

        uplimit = self._limits_conf.max_messages_per_claim_or_pop
        if limit is not None and not (0 < limit <= uplimit):
            msg = _(u'Limit must be at least 1 and may not '
                    'be greater than {0}.')

            raise ValidationFailed(
                msg, self._limits_conf.max_messages_per_claim_or_pop)

        grace = metadata['grace']

        if not (MIN_CLAIM_GRACE <= grace <= self._limits_conf.max_claim_grace):
            msg = _(u'The grace for a claim may not exceed {0} seconds, and '
                    'must be at least {1} seconds long.')

            raise ValidationFailed(
                msg, self._limits_conf.max_claim_grace, MIN_CLAIM_GRACE)

    def claim_updating(self, metadata):
        """Restrictions on the claim TTL.

        :param metadata: The claim metadata
        :raises: ValidationFailed if the TTL is out of range
        """

        ttl = metadata['ttl']

        if not (MIN_CLAIM_TTL <= ttl <= self._limits_conf.max_claim_ttl):
            msg = _(u'The TTL for a claim may not exceed {0} seconds, and '
                    'must be at least {1} seconds long.')

            raise ValidationFailed(
                msg, self._limits_conf.max_message_ttl, MIN_CLAIM_TTL)

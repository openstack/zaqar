# Copyright (c) 2013 Rackspace, Inc.
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

import datetime
import re

from oslo_config import cfg
from oslo_utils import timeutils
import six

from zaqar.i18n import _

MIN_MESSAGE_TTL = 60
MIN_CLAIM_TTL = 60
MIN_CLAIM_GRACE = 60
MIN_SUBSCRIPTION_TTL = 60
_PURGBLE_RESOURCE_TYPES = {'messages', 'subscriptions'}

_TRANSPORT_LIMITS_OPTIONS = (
    cfg.IntOpt('max_queues_per_page', default=20,
               deprecated_name='queue_paging_uplimit',
               deprecated_group='limits:transport',
               help='Defines the maximum number of queues per page.'),

    cfg.IntOpt('max_messages_per_page', default=20,
               deprecated_name='message_paging_uplimit',
               deprecated_group='limits:transport',
               help='Defines the maximum number of messages per page.'),

    cfg.IntOpt('max_subscriptions_per_page', default=20,
               deprecated_name='subscription_paging_uplimit',
               deprecated_group='limits:transport',
               help='Defines the maximum number of subscriptions per page.'),

    cfg.IntOpt('max_messages_per_claim_or_pop', default=20,
               deprecated_name='max_messages_per_claim',
               help='The maximum number of messages that can be claimed (OR) '
                    'popped in a single request'),

    cfg.IntOpt('max_queue_metadata', default=64 * 1024,
               deprecated_name='metadata_size_uplimit',
               deprecated_group='limits:transport',
               help='Defines the maximum amount of metadata in a queue.'),

    cfg.IntOpt('max_messages_post_size', default=256 * 1024,
               deprecated_name='message_size_uplimit',
               deprecated_group='limits:transport',
               deprecated_opts=[cfg.DeprecatedOpt('max_message_size')],
               help='Defines the maximum size of message posts.'),

    cfg.IntOpt('max_message_ttl', default=1209600,
               deprecated_name='message_ttl_max',
               deprecated_group='limits:transport',
               help='Maximum amount of time a message will be available.'),

    cfg.IntOpt('max_claim_ttl', default=43200,
               deprecated_name='claim_ttl_max',
               deprecated_group='limits:transport',
               help='Maximum length of a message in claimed state.'),

    cfg.IntOpt('max_claim_grace', default=43200,
               deprecated_name='claim_grace_max',
               deprecated_group='limits:transport',
               help='Defines the maximum message grace period in seconds.'),

    cfg.ListOpt('subscriber_types', default=['http', 'https', 'mailto',
                                             'trust+http', 'trust+https'],
                help='Defines supported subscriber types.'),

    cfg.IntOpt('max_flavors_per_page', default=20,
               help='Defines the maximum number of flavors per page.'),

    cfg.IntOpt('max_pools_per_page', default=20,
               help='Defines the maximum number of pools per page.'),
)

_TRANSPORT_LIMITS_GROUP = 'transport'

# NOTE(kgriffs): Don't use \w because it isn't guaranteed to match
# only ASCII characters.
QUEUE_NAME_REGEX = re.compile('^[a-zA-Z0-9_\-.]+$')
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
        self._supported_operations = ('add', 'remove', 'replace')

    def queue_identification(self, queue, project):
        """Restrictions on a project id & queue name pair.

        :param queue: Name of the queue
        :param project: Project id
        :raises ValidationFailed: if the `name` is longer than 64
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

    def _get_change_operation_d10(self, raw_change):
        op = raw_change.get('op')
        if op is None:
            msg = (_('Unable to find `op` in JSON Schema change. '
                     'It must be one of the following: %(available)s.') %
                   {'available': ', '.join(self._supported_operations)})
            raise ValidationFailed(msg)
        if op not in self._supported_operations:
            msg = (_('Invalid operation: `%(op)s`. '
                     'It must be one of the following: %(available)s.') %
                   {'op': op,
                    'available': ', '.join(self._supported_operations)})
            raise ValidationFailed(msg)
        return op

    def _get_change_path_d10(self, raw_change):
        try:
            return raw_change['path']
        except KeyError:
            msg = _("Unable to find '%s' in JSON Schema change") % 'path'
            raise ValidationFailed(msg)

    def _decode_json_pointer(self, pointer):
        """Parse a json pointer.

        Json Pointers are defined in
        http://tools.ietf.org/html/draft-pbryan-zyp-json-pointer .
        The pointers use '/' for separation between object attributes, such
        that '/A/B' would evaluate to C in {"A": {"B": "C"}}. A '/' character
        in an attribute name is encoded as "~1" and a '~' character is encoded
        as "~0".
        """
        self._validate_json_pointer(pointer)
        ret = []
        for part in pointer.lstrip('/').split('/'):
            ret.append(part.replace('~1', '/').replace('~0', '~').strip())
        return ret

    def _validate_json_pointer(self, pointer):
        """Validate a json pointer.

        We only accept a limited form of json pointers.
        """
        if not pointer.startswith('/'):
            msg = _('Pointer `%s` does not start with "/".') % pointer
            raise ValidationFailed(msg)
        if re.search('/\s*?/', pointer[1:]):
            msg = _('Pointer `%s` contains adjacent "/".') % pointer
            raise ValidationFailed(msg)
        if len(pointer) > 1 and pointer.endswith('/'):
            msg = _('Pointer `%s` end with "/".') % pointer
            raise ValidationFailed(msg)
        if pointer[1:].strip() == '/':
            msg = _('Pointer `%s` does not contains valid token.') % pointer
            raise ValidationFailed(msg)
        if re.search('~[^01]', pointer) or pointer.endswith('~'):
            msg = _('Pointer `%s` contains "~" not part of'
                    ' a recognized escape sequence.') % pointer
            raise ValidationFailed(msg)

    def _get_change_value(self, raw_change, op):
        if 'value' not in raw_change:
            msg = _('Operation "{0}" requires a member named "value".')
            raise ValidationFailed(msg, op)
        return raw_change['value']

    def _validate_change(self, change):
        if change['op'] == 'remove':
            return
        path_root = change['path'][0]
        if len(change['path']) >= 1 and path_root.lower() != 'metadata':
            msg = _("The root of path must be metadata, e.g /metadata/key.")
            raise ValidationFailed(msg)

    def _validate_path(self, op, path):
        limits = {'add': 2, 'remove': 2, 'replace': 2}
        if len(path) != limits.get(op, 2):
            msg = _("Invalid JSON pointer for this resource: "
                    "'/%s, e.g /metadata/key'") % '/'.join(path)
            raise ValidationFailed(msg)

    def _parse_json_schema_change(self, raw_change, draft_version):
        if draft_version == 10:
            op = self._get_change_operation_d10(raw_change)
            path = self._get_change_path_d10(raw_change)
        else:
            msg = _('Unrecognized JSON Schema draft version')
            raise ValidationFailed(msg)

        path_list = self._decode_json_pointer(path)
        return op, path_list

    def _validate_retry_policy(self, metadata):
        retry_policy = metadata.get('_retry_policy') if metadata else None
        if retry_policy and not isinstance(retry_policy, dict):
            msg = _('retry_policy must be a dict.')
            raise ValidationFailed(msg)

        if retry_policy:
            valid_keys = ['retries_with_no_delay', 'minimum_delay_retries',
                          'minimum_delay', 'maximum_delay',
                          'maximum_delay_retries', 'retry_backoff_function',
                          'ignore_subscription_override']
            for key in valid_keys:
                retry_value = retry_policy.get(key)
                if key == 'retry_backoff_function':
                    if retry_value and not isinstance(retry_value, str):
                        msg = _('retry_backoff_function must be a string.')
                        raise ValidationFailed(msg)
                    # TODO(wanghao): Now we only support linear function.
                    # This will be removed after we support more functions.
                    if retry_value and retry_value != 'linear':
                        msg = _('retry_backoff_function only supports linear '
                                'now.')
                        raise ValidationFailed(msg)
                elif key == 'ignore_subscription_override':
                    if retry_value and not isinstance(retry_value, bool):
                        msg = _('ignore_subscription_override must be a '
                                'boolean.')
                        raise ValidationFailed(msg)
                else:
                    if retry_value and not isinstance(retry_value, int):
                        msg = _('Retry policy: %s must be a integer.') % key
                        raise ValidationFailed(msg)

    def queue_patching(self, request, changes):
        washed_changes = []
        content_types = {
            'application/openstack-messaging-v2.0-json-patch': 10,
        }

        json_schema_version = content_types[request.content_type]

        if not isinstance(changes, list):
            msg = _('Request body must be a JSON array of operation objects.')
            raise ValidationFailed(msg)

        for raw_change in changes:
            if not isinstance(raw_change, dict):
                msg = _('Operations must be JSON objects.')
                raise ValidationFailed(msg)

            (op, path) = self._parse_json_schema_change(raw_change,
                                                        json_schema_version)

            # NOTE(flwang): Now the 'path' is a list.
            self._validate_path(op, path)
            change = {'op': op, 'path': path,
                      'json_schema_version': json_schema_version}

            if not op == 'remove':
                change['value'] = self._get_change_value(raw_change, op)

            self._validate_change(change)

            washed_changes.append(change)

        return washed_changes

    def queue_listing(self, limit=None, **kwargs):
        """Restrictions involving a list of queues.

        :param limit: The expected number of queues in the list
        :param kwargs: Ignored arguments passed to storage API
        :raises ValidationFailed: if the limit is exceeded
        """

        uplimit = self._limits_conf.max_queues_per_page
        if limit is not None and not (0 < limit <= uplimit):
            msg = _(u'Limit must be at least 1 and no greater than {0}.')
            raise ValidationFailed(msg, self._limits_conf.max_queues_per_page)

    def queue_metadata_length(self, content_length):
        """Restrictions on queue's length.

        :param content_length: Queue request's length.
        :raises ValidationFailed: if the metadata is oversize.
        """
        if content_length is None:
            return
        if content_length > self._limits_conf.max_queue_metadata:
            msg = _(u'Queue metadata is too large. Max size: {0}')
            raise ValidationFailed(msg, self._limits_conf.max_queue_metadata)

    def queue_metadata_putting(self, queue_metadata):
        """Checking if the reserved attributes of the queue are valid.

        :param queue_metadata: Queue's metadata.
        :raises ValidationFailed: if any reserved attribute is invalid.
        """
        if not queue_metadata:
            return

        queue_default_ttl = queue_metadata.get('_default_message_ttl')
        if queue_default_ttl and not isinstance(queue_default_ttl, int):
            msg = _(u'_default_message_ttl must be integer.')
            raise ValidationFailed(msg)

        if queue_default_ttl:
            if not (MIN_MESSAGE_TTL <= queue_default_ttl <=
                    self._limits_conf.max_message_ttl):
                msg = _(u'_default_message_ttl can not exceed {0} '
                        'seconds, and must be at least {1} seconds long.')
                raise ValidationFailed(
                    msg, self._limits_conf.max_message_ttl, MIN_MESSAGE_TTL)

        queue_max_msg_size = queue_metadata.get('_max_messages_post_size',
                                                None)
        if queue_max_msg_size and not isinstance(queue_max_msg_size, int):
            msg = _(u'_max_messages_post_size must be integer.')
            raise ValidationFailed(msg)

        if queue_max_msg_size:
            if not (0 < queue_max_msg_size <=
                    self._limits_conf.max_messages_post_size):
                raise ValidationFailed(
                    _(u'_max_messages_post_size can not exceed {0}, '
                      ' and must be at least greater than 0.'),
                    self._limits_conf.max_messages_post_size)

        max_claim_count = queue_metadata.get('_max_claim_count', None)
        if max_claim_count and not isinstance(max_claim_count, int):
            msg = _(u'_max_claim_count must be integer.')
            raise ValidationFailed(msg)

        dlq_ttl = queue_metadata.get('_dead_letter_queue_messages_ttl', None)
        if dlq_ttl and not isinstance(dlq_ttl, int):
            msg = _(u'_dead_letter_queue_messages_ttl must be integer.')
            raise ValidationFailed(msg)

        if dlq_ttl and not (MIN_MESSAGE_TTL <= dlq_ttl <=
                            self._limits_conf.max_message_ttl):
            msg = _(u'The TTL for a message may not exceed {0} seconds, '
                    'and must be at least {1} seconds long.')
            raise ValidationFailed(msg, self._limits_conf.max_message_ttl,
                                   MIN_MESSAGE_TTL)

        self._validate_retry_policy(queue_metadata)

    def queue_purging(self, document):
        """Restrictions the resource types to be purged for a queue.

        :param resource_types: Type list of all resource under a queue
        :raises ValidationFailed: if the resource types are invalid
        """

        if 'resource_types' not in document:
            msg = _(u'Post body must contain key "resource_types".')
            raise ValidationFailed(msg)

        if (not set(document['resource_types']).issubset(
                _PURGBLE_RESOURCE_TYPES)):
            msg = _(u'Resource types must be a sub set of {0}.')
            raise ValidationFailed(msg, _PURGBLE_RESOURCE_TYPES)

    def message_posting(self, messages):
        """Restrictions on a list of messages.

        :param messages: A list of messages
        :raises ValidationFailed: if any message has a out-of-range
            TTL.
        """

        if not messages:
            raise ValidationFailed(_(u'No messages to enqueu.'))

        for msg in messages:
            self.message_content(msg)

    def message_length(self, content_length, max_msg_post_size=None):
        """Restrictions on message post length.

        :param content_length: Queue request's length.
        :raises ValidationFailed: if the metadata is oversize.
        """
        if content_length is None:
            return

        if max_msg_post_size:
            try:
                min_max_size = min(max_msg_post_size,
                                   self._limits_conf.max_messages_post_size)
                if content_length > min_max_size:
                    raise ValidationFailed(
                        _(u'Message collection size is too large. The max '
                          'size for current queue is {0}. It is calculated '
                          'by max size = min(max_messages_post_size_config: '
                          '{1}, max_messages_post_size_queue: {2}).'),
                        min_max_size,
                        self._limits_conf.max_messages_post_size,
                        max_msg_post_size)
            except TypeError:
                # NOTE(flwang): If there is a type error when using min(),
                # it only happens in py3.x, it will be skipped and compare
                # the message length with the size defined in config file.
                pass

        if content_length > self._limits_conf.max_messages_post_size:
            raise ValidationFailed(
                _(u'Message collection size is too large. Max size {0}'),
                self._limits_conf.max_messages_post_size)

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
        :raises ValidationFailed: if the limit is exceeded
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
        :raises ValidationFailed: if,
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
        :raises ValidationFailed: if either TTL or grace is out of range,
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
        :raises ValidationFailed: if the TTL is out of range
        """

        ttl = metadata['ttl']

        if not (MIN_CLAIM_TTL <= ttl <= self._limits_conf.max_claim_ttl):
            msg = _(u'The TTL for a claim may not exceed {0} seconds, and '
                    'must be at least {1} seconds long.')

            raise ValidationFailed(
                msg, self._limits_conf.max_claim_ttl, MIN_CLAIM_TTL)

    def subscription_posting(self, subscription):
        """Restrictions on a creation of subscription.

        :param subscription: dict of subscription
        :raises ValidationFailed: if the subscription is invalid.
        """
        for p in ('subscriber',):
            if p not in subscription.keys():
                raise ValidationFailed(_(u'Missing parameter %s in body.') % p)

        self.subscription_patching(subscription)

    def subscription_patching(self, subscription):
        """Restrictions on an update of subscription.

        :param subscription: dict of subscription
        :raises ValidationFailed: if the subscription is invalid.
        """

        if not subscription:
            raise ValidationFailed(_(u'No subscription to create.'))

        if not isinstance(subscription, dict):
            msg = _('Subscriptions must be a dict.')
            raise ValidationFailed(msg)

        subscriber = subscription.get('subscriber')
        subscriber_type = None

        if subscriber:
            parsed_uri = six.moves.urllib_parse.urlparse(subscriber)
            subscriber_type = parsed_uri.scheme

            if subscriber_type not in self._limits_conf.subscriber_types:
                msg = _(u'The subscriber type of subscription must be '
                        u'supported in the list {0}.')
                raise ValidationFailed(msg, self._limits_conf.subscriber_types)

        options = subscription.get('options')
        if options and not isinstance(options, dict):
            msg = _(u'Options must be a dict.')
            raise ValidationFailed(msg)

        self._validate_retry_policy(options)

        ttl = subscription.get('ttl')
        if ttl:
            if not isinstance(ttl, int):
                msg = _(u'TTL must be an integer.')
                raise ValidationFailed(msg)

            if ttl < MIN_SUBSCRIPTION_TTL:
                msg = _(u'The TTL for a subscription '
                        'must be at least {0} seconds long.')
                raise ValidationFailed(msg, MIN_SUBSCRIPTION_TTL)

            # NOTE(flwang): By this change, technically, user can set a very
            # big TTL so as to get a very long subscription.
            now = timeutils.utcnow_ts()
            now_dt = datetime.datetime.utcfromtimestamp(now)
            msg = _(u'The TTL seconds for a subscription plus current time'
                    ' must be less than {0}.')
            try:
                # NOTE(flwang): If below expression works, then we believe the
                # ttl is acceptable otherwise it exceeds the max time of
                # python.
                now_dt + datetime.timedelta(seconds=ttl)
            except OverflowError:
                raise ValidationFailed(msg, datetime.datetime.max)

    def subscription_confirming(self, confirmed):
        confirmed = confirmed.get('confirmed')
        if not isinstance(confirmed, bool):
            msg = _(u"The 'confirmed' should be boolean.")
            raise ValidationFailed(msg)

    def subscription_listing(self, limit=None, **kwargs):
        """Restrictions involving a list of subscriptions.

        :param limit: The expected number of subscriptions in the list
        :param kwargs: Ignored arguments passed to storage API
        :raises ValidationFailed: if the limit is exceeded
        """

        uplimit = self._limits_conf.max_subscriptions_per_page
        if limit is not None and not (0 < limit <= uplimit):
            msg = _(u'Limit must be at least 1 and may not '
                    'be greater than {0}.')

            raise ValidationFailed(
                msg, self._limits_conf.max_subscriptions_per_page)

    def get_limit_conf_value(self, limit_conf_name=None):
        """Return the value of limit configuration.

        :param limit_conf_name: configuration name
        """
        return self._limits_conf[limit_conf_name]

    def flavor_listing(self, limit=None, **kwargs):
        """Restrictions involving a list of pools.

        :param limit: The expected number of flavors in the list
        :param kwargs: Ignored arguments passed to storage API
        :raises ValidationFailed: if the limit is exceeded
        """

        uplimit = self._limits_conf.max_flavors_per_page
        if limit is not None and not (0 < limit <= uplimit):
            msg = _(u'Limit must be at least 1 and no greater than {0}.')
            raise ValidationFailed(msg, self._limits_conf.max_flavors_per_page)

    def pool_listing(self, limit=None, **kwargs):
        """Restrictions involving a list of pools.

        :param limit: The expected number of flavors in the list
        :param kwargs: Ignored arguments passed to storage API
        :raises ValidationFailed: if the limit is exceeded
        """

        uplimit = self._limits_conf.max_pools_per_page
        if limit is not None and not (0 < limit <= uplimit):
            msg = _(u'Limit must be at least 1 and no greater than {0}.')
            raise ValidationFailed(msg, self._limits_conf.max_pools_per_page)

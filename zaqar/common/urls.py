# Copyright (c) 2015 Red Hat, Inc.
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
import hashlib
import hmac

from oslo_utils import timeutils
import six

_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'


def create_signed_url(key, paths, project=None, expires=None, methods=None):
    """Creates a signed url for the specified path

    This function will create a pre-signed URL for `path` using the
    specified `options` or the default ones. The signature will be the
    hex value of the hmac created using `key`

    :param key: A string to use as a `key` for the hmac generation.
    :param paths: A list of strings representing URL paths.
    :param project: (Default None) The ID of the project this URL belongs to.
    :param methods: (Default ['GET']) A list of methods that will be
        supported by the generated URL.
    :params expires: (Default time() + 86400) The expiration date for
        the generated URL.
    """

    methods = methods or ['GET']

    if key is None:
        raise ValueError('The `key` can\'t be None')

    if not isinstance(paths, list) or not paths:
        raise ValueError('`paths` must be a non-empty list')

    if not isinstance(methods, list):
        raise ValueError('`methods` should be a list')

    # NOTE(flaper87): The default expiration time is 1day
    # Evaluate whether this should be configurable. We may
    # also want to have a "maximum" expiration time. Food
    # for thoughts.
    if expires is not None:
        # NOTE(flaper87): Verify if the format is correct
        # and normalize the value to UTC.
        check_expires = None
        try:
            check_expires = int(expires)
        except ValueError:
            pass
        if check_expires:
            raise ValueError('`expires` should be date format, '
                             'for example 2016-01-01T00:00:00, '
                             'not integer value: %s' % check_expires)
        parsed = timeutils.parse_isotime(expires)
        expires = timeutils.normalize_time(parsed)
    else:
        delta = datetime.timedelta(days=1)
        expires = timeutils.utcnow() + delta

    if expires <= timeutils.utcnow():
        raise ValueError('`expires` is lower than the current time')

    methods = sorted(methods)
    paths = sorted(paths)
    expires_str = expires.strftime(_DATE_FORMAT)
    hmac_body = six.b(r'%(paths)s\n%(methods)s\n%(project)s\n%(expires)s' %
                      {'paths': ','.join(paths), 'methods': ','.join(methods),
                       'project': project, 'expires': expires_str})

    if not isinstance(key, six.binary_type):
        key = six.binary_type(key.encode('utf-8'))

    return {'paths': paths,
            'methods': methods,
            'project': project,
            'expires': expires_str,
            'signature': hmac.new(key, hmac_body, hashlib.sha256).hexdigest()}


def verify_signed_headers_data(key, paths, project,
                               signature, methods, expires):
    """Verify that `signature` matches for the given values

    :param key: A string to use as a `key` for the hmac generation.
    :param paths: A list of strings representing URL paths.
    :param project: The ID of the project this URL belongs to.
    :param signature: The pre-generated signature
    :param methods: A list of methods that will be
        supported by the generated URL.
    :params expires: The expiration date for
        the generated URL.
    """

    generated = create_signed_url(key, paths, project=project,
                                  methods=methods, expires=expires)

    return signature == generated['signature']

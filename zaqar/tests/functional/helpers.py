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

import random
import string
import uuid


def create_zaqar_headers(conf):
    """Returns headers to be used for all Zaqar requests."""

    headers = {
        "User-Agent": conf.headers.user_agent,
        "Accept": "application/json",
        "X-Project-ID": conf.headers.project_id,
        "Client-ID": str(uuid.uuid1()),
    }

    return headers


def generate_dict(dict_length):
    """Returns dictionary of specified length. Key:Value is random data.

    :param dict_length: length of the dictionary
    """
    return dict([(generate_random_string(), generate_random_string())
                for _ in range(dict_length)])


def generate_random_string(length=10):
    """Returns an ASCII string of specified length."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for i in range(length))


def single_message_body(messagesize=2, default_ttl=False, ttl=None):
    """Returns message body for one message.

    :param messagesize: Size of the message body to generate (default 2)
    :param default_ttl: Set to True to not set an explicit TTL value in
        the message request, in which case the server will use a default
        value (default False). Note that default TTL is only supported in
        v1.1 of the API.
    :param ttl: Number of seconds to provide as the TTL for each
        message. If not specified, a random value is chosen in the
        range: (60 <= TTL <= 1209600). If `default_ttl` is True, the
        `ttl` param is ignored.
    """

    message_body = {}
    message_body['body'] = generate_dict(messagesize)

    if not default_ttl:
        if ttl is not None:
            message_body['ttl'] = ttl
        else:
            message_body['ttl'] = random.randint(60, 1209600)

    return message_body


def create_message_body(messagecount, **kwargs):
    """Returns request body for message-posting tests.

    :param messagecount: Number of messages to create
    :param **kwargs: Same as for `single_message_body`
    """

    return [single_message_body(**kwargs)
            for i in range(messagecount)]


def create_message_body_v1_1(messagecount, **kwargs):
    """Returns request body for message-posting tests.

    :param messagecount: Number of messages to create
    :param **kwargs: Same as for `single_message_body`
    """

    return {
        "messages": [single_message_body(**kwargs)
                     for i in range(messagecount)]
    }


def create_pool_body(**kwargs):
    pool_body = {
        'weight': kwargs['weight'],
        'uri': kwargs['uri'],
        'options': {
            'max_retry_sleep': 1,
            'partitions': 8
        }
    }

    return pool_body


def create_subscription_body(subscriber='http://fake:8080', ttl=600,
                             options_key='funny', options_value='no'):
    options = {options_key: options_value}
    return {'subscriber': subscriber, 'options': options, 'ttl': ttl}

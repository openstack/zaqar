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


def get_keystone_token(conf, client):
    """Gets Keystone Auth token."""
    body = {
        'auth': {
            'passwordCredentials': {
                'username': conf.auth.username,
                'password': conf.auth.password
            },
        },
    }

    header = {"Content-Type": "application/json",
              "Accept": "application/json"}

    response = client.post(url=conf.auth.url,
                           headers=header,
                           data=body)

    response_body = response.json()
    return response_body['access']['token']['id']


def create_marconi_headers(conf):
    """Returns headers to be used for all Marconi requests."""

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


def single_message_body(**kwargs):
    """Returns message body for one message .

    The ttl will be a random value (60 <= TTL <= 1209600).
    The message body will be random dict.
    :param **kwargs: can be {messagesize: x} , where x is message size
    :param **kwargs: can be {ttl: x} , where x is ttl in seconds
    """
    valid_ttl = random.randint(60, 1209600)

    if 'messagesize' in kwargs.keys():
        body = generate_dict(kwargs['messagesize'])
    else:
        body = generate_dict(2)

    if 'ttl' in kwargs:
        ttl = kwargs['ttl']
    else:
        ttl = valid_ttl

    message_body = {'ttl': ttl, 'body': body}
    return message_body


def create_message_body(**kwargs):
    """Returns request body for post message tests.

    :param **kwargs: can be {messagecount: x} , x is the # of messages.
    """
    message_count = kwargs['messagecount']
    return [single_message_body(**kwargs) for i in range(message_count)]


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

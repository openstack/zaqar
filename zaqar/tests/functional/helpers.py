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


def generate_random_string(length=10):
    """Returns an ASCII string of specified length."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for i in range(length))


def create_subscription_body(subscriber='http://fake:8080', ttl=600,
                             options_key='funny', options_value='no'):
    options = {options_key: options_value}
    return {'subscriber': subscriber, 'options': options, 'ttl': ttl}

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

import binascii
import json
import os

from marconi.tests.system.common import functionlib
from marconi.tests.system.common import http


def verify_queue_stats(*get_response):
    """Verifies GET queue/stats response.

    Verification Steps:
       1. stats json body has the keys - action & messages.
       2. messages json has the keys - claimed & free.
       3. claimed & free key values are int.
    :param *getresponse: [headers, body] returned for get queue stats.
    """

    test_result_flag = True
    headers = get_response[0]
    body = json.loads(get_response[1])

    keys_in_body = body.keys()
    keys_in_body.sort()

    if (keys_in_body == ['actions', 'messages']):
        stats = body['messages']
        keys_in_stats = stats.keys()
        keys_in_stats.sort()
        if (keys_in_stats == ['claimed', 'free']):
            try:
                int(stats['claimed'])
                int(stats['free'])
            except Exception:
                test_result_flag = False
        else:
            test_result_flag = False
    else:
        test_result_flag = False

    if test_result_flag:
        return test_result_flag
    else:
        print headers
        print body
        assert test_result_flag, 'Get Request stats failed'


def get_queue_name(namelength=65):
    """Returns a queuename of specified length.

    By default, a name longer than Marconi allows - currently 64 char.
    :param namelength: length of the queue name.
    """

    appender = '/queues/' + binascii.b2a_hex(os.urandom(namelength))
    url = functionlib.create_url_from_appender(appender)
    return url


def verify_list_queues(*list_queue_response):
    """Verifies the response of list queues.

    :param *list_queue_response: [header, body] returned for list queue.
    """
    response_body = json.loads(list_queue_response[1])
    links = response_body['links']
    href = links[0]['href']
    detail_enabled = 'detailed=true' in href

    queue_list = response_body['queues']
    test_result_flags = [verify_listed(queue, detail_enabled)
                         for queue in queue_list]

    if False in test_result_flags:
        test_result_flag = False
        print 'List Queue API response: {}'.format(response_body)
        assert test_result_flag, 'List Queue failed'

    if links[0]['rel'] == 'next':
        list_queues(href)


def verify_listed(queue, detail_enabled):
    """Verifies the listed queues.

    :param queue: queue returned in the list queues response.
    :param detail_enabled: indicates if queue contains metadata
    """
    test_result_flag = True

    keys = queue.keys()
    keys.sort()

    if detail_enabled:
        expected_keys = ['href', 'metadata', 'name']
    else:
        expected_keys = ['href', 'name']

    if keys == expected_keys:
        return test_result_flag
    else:
        print 'list_queue response does not match expected response'
        print queue
        test_result_flag = False

    return test_result_flag


def list_queues(href):
    """Lists queue using the href value.

    :param href: href returned by a previous list queue request.
    """
    test_result_flag = False

    url = functionlib.create_url_from_appender(href)
    header = functionlib.create_marconi_headers()

    list_queue_response = http.get(url, header)
    if list_queue_response.status_code == 200:
        headers = list_queue_response.headers
        text = list_queue_response.text
        verify_list_queues(headers, text)
    elif list_queue_response.status_code == 204:
        test_result_flag = True
    else:
        assert test_result_flag, 'List Queue failed'

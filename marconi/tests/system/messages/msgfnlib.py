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

from __future__ import with_statement
import json
import random

from marconi.tests.system.common import config
from marconi.tests.system.common import functionlib
from marconi.tests.system.common import http


cfg = config.Config()


def generate_dict(dict_length):
    """Returns dictionary of specified length. Key:Value is random data."""
    with open('/usr/share/dict/words', 'rt') as f:
        words = f.readlines()
    words = [w.rstrip() for w in words]

    dict = {}
    while len(dict) < dict_length:
        key, value = random.sample(words, 2)
        dict.update({key: value})
    return dict


def single_message_body(**kwargs):
    """Returns message body for one message .

    The ttl will be a random value (60 <= TTL <= 1209600).
    The message body will be random dict.
    :param **kwargs can be {messagesize: x} , where x is message size
    :param **kwargs can be {ttl: x} , where x is ttl in seconds
    """
    valid_ttl = random.randint(60, 1209600)

    if "messagesize" in kwargs.keys():
        body = generate_dict(kwargs["messagesize"])
    else:
        body = generate_dict(2)

    if "ttl" in kwargs.keys():
        ttl = kwargs["ttl"]
    else:
        ttl = valid_ttl

    message_body = {"ttl": ttl, "body": body}
    return message_body


def get_message_body(**kwargs):
    """Returns request body for post message tests.

    :param **kwargs can be {messagecount: x} , where x is the # of messages.
    """
    message_count = kwargs["messagecount"]
    multiple_message_body = []
    i = 0
    while i < message_count:
        message_body = single_message_body(**kwargs)
        multiple_message_body.append(message_body)
        i = i + 1
    return multiple_message_body


def dummyget_message_body(dict):
    """Dummy function since Robot framework does not support **kwargs."""
    dict = get_message_body(**dict)
    return dict


def create_url(base_url=cfg.base_url, *msg_id_list):
    """Creates url list for retrieving messages with message id."""
    url = [(base_url + msg_id) for msg_id in msg_id_list]
    return url


def verify_msg_length(count=10, *msg_list):
    """Verifies the number of messages returned.

    :param count: limit specified in the GET url.
    :param *msg_list : list of message returned in the GET.
    """
    test_result_flag = False
    msg_body = json.loads(msg_list[0])
    msg_list = msg_body["messages"]
    msg_count = len(msg_list)
    if (msg_count <= count):
        test_result_flag = True
    else:
        return test_result_flag
    return test_result_flag


def get_href(*msg_list):
    """Extracts href."""
    msg_body = json.loads(msg_list[0])
    link = msg_body["links"]
    href = link[0]["href"]
    return href


def verify_post_msg(msg_headers, posted_body):
    """Verifies the response of POST Message(s).

    Retrieves the posted Message(s) & validates the message metadata.
    """
    test_result_flag = False

    location = msg_headers['location']
    url = functionlib.create_url_from_appender(location)
    header = functionlib.create_marconi_headers()

    getmsg = http.get(url, header)
    if getmsg.status_code == 200:
        test_result_flag = functionlib.verify_metadata(getmsg.text,
                                                       posted_body)
    else:
        print("Failed to GET {}".format(url))
        print("Request Header")
        print header
        print("Response Headers")
        print getmsg.headers
        print("Response Body")
        print getmsg.text
        assert test_result_flag, "HTTP code {}".format(getmsg.status_code)


def get_next_msgset(responsetext):
    """Follows the href path & GETs the next batch of messages recursively."""
    test_result_flag = False

    href = get_href(responsetext)
    url = functionlib.create_url_from_appender(href)
    header = functionlib.create_marconi_headers()

    getmsg = http.get(url, header)
    if getmsg.status_code == 200:
        return get_next_msgset(getmsg.text)
    elif getmsg.status_code == 204:
        test_result_flag = True
        return test_result_flag
    else:
        test_result_flag = False
        print("Failed to GET {}".format(url))
        print(getmsg.text)
        assert test_result_flag, "HTTP code {}".format(getmsg.status_code)


def verify_get_msgs(count, *getresponse):
    """Verifies GET message & does a recursive GET if needed."""
    test_result_flag = False

    body = getresponse[1]

    msglengthflag = verify_msg_length(count, body)
    if msglengthflag:
        test_result_flag = get_next_msgset(body)
    else:
        print("Messages returned exceed requested number of messages")
        test_result_flag = False

    if not test_result_flag:
        assert test_result_flag, "Recursive Get Messages Failed"


def delete_msg(*postresponse):
    """Post DELETE message & verifies that a subsequent GET returns 404."""
    test_result_flag = False
    headers = str(postresponse[0])
    headers = headers.replace("'", '"')
    headers = json.loads(headers)
    location = headers['location']
    url = functionlib.create_url_from_appender(location)
    header = functionlib.create_marconi_headers()
    deletemsg = http.delete(url, header)
    if deletemsg.status_code == 204:
        test_result_flag = functionlib.verify_delete(url, header)
    else:
        print("DELETE message failed")
        print("URL")
        print url
        print("headers")
        print header
        print("Response Body")
        print deletemsg.text
        assert test_result_flag, "DELETE Code {}".format(deletemsg.status_code)

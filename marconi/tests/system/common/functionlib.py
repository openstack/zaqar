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

from marconi.tests.system.common import config
from marconi.tests.system.common import http


CFG = config.Config()


def get_keystone_token():
    """Gets Keystone Auth token."""
    req_json = {
        'auth': {
        'passwordCredentials': {
        'username': CFG.username,
        'password': CFG.password
        }
        },
    }

    header = '{"Host":  "identity.api.rackspacecloud.com",'
    header += '"Content-Type": "application/json","Accept":"application/json"}'
    url = CFG.auth_url

    response = http.post(url=url, header=header, body=req_json)
    response_body = json.loads(response.text)

    auth_token = response_body['access']['token']['id']

    return auth_token


def get_auth_token():
    """Returns a valid auth token if auth is turned on."""
    if CFG.auth_enabled == 'true':
        auth_token = get_keystone_token()
    else:
        auth_token = 'notrealtoken'

    return auth_token


def create_marconi_headers():
    """Returns headers to be used for all Marconi requests."""
    auth_token = get_auth_token()

    headers = '{"Host": "<HOST>","User-Agent": "<USER-AGENT>","Date":"<DATE>",'
    headers += '"Accept":  "application/json","Accept-Encoding":  "gzip",'
    headers += '"X-Auth-Token":  "<auth_token>","Client-ID":  "<UUID>"}'
    headers = headers.replace('<auth_token>', auth_token)
    headers = headers.replace('<HOST>', CFG.host)
    headers = headers.replace('<USER-AGENT>', CFG.user_agent)
    headers = headers.replace('<UUID>', CFG.uuid)

    return headers


def invalid_auth_token_header():
    """Returns a header with invalid auth token."""
    auth_token = get_auth_token()

    headers = '{"Host":"<HOST>","User-Agent":"<USER-AGENT>","Date":"<DATE>",'
    headers += '"Accept":  "application/json","Accept-Encoding":  "gzip",'
    headers += 'X-Auth-Token:  <auth_token>}'
    headers = headers.replace('<auth_token>', auth_token)
    headers = headers.replace('<HOST>', CFG.host)
    headers = headers.replace('<USER-AGENT>', CFG.user_agent)

    return headers


def missing_header_fields():
    """Returns a header with missing USER_AGENT header."""
    auth_token = get_auth_token()

    headers = '{"Host":  "<HOST>","Date":  "<DATE>",'
    headers += '"Accept":  "application/json","Accept-Encoding":  "gzip",'
    headers += '"X-Auth-Token":  "<auth_token>"}'
    headers = headers.replace('<auth_token>', auth_token)
    headers = headers.replace('<HOST>', CFG.host)

    return headers


def plain_text_in_header():
    """Returns headers to be used for all Marconi requests."""
    auth_token = get_auth_token()

    headers = '{"Host":"<HOST>","User-Agent":"<USER-AGENT>","Date":"<DATE>",'
    headers += '"Accept":  "text/plain","Accept-Encoding":  "gzip",'
    headers += '"X-Auth-Token":  "<auth_token>"}'
    headers = headers.replace('<auth_token>', auth_token)
    headers = headers.replace('<HOST>', CFG.host)
    headers = headers.replace('<USER-AGENT>', CFG.user_agent)

    return headers


def asterisk_in_header():
    """Returns headers to be used for all Marconi requests."""
    auth_token = get_auth_token()

    headers = '{"Host":"<HOST>","User-Agent":"<USER-AGENT>","Date":"<DATE>",'
    headers += '"Accept":  "*/*","Accept-Encoding":  "gzip",'
    headers += '"X-Auth-Token":  "<auth_token>"}'
    headers = headers.replace('<auth_token>', auth_token)
    headers = headers.replace('<HOST>', CFG.host)
    headers = headers.replace('<USER-AGENT>', CFG.user_agent)

    return headers


def get_headers(input_header):
    """Creates http request headers.

    1. If header value is specified in the test_data.csv, that will be used.
    2. Headers can also be substituted in the Robot test case definition
    file (*_tests.txt)
    3. If 1. & 2. is not true -->
      Replaces the header data with generic Marconi headers.
    """
    if input_header:
        header = input_header
    else:
        header = create_marconi_headers()

    return header


def get_custom_body(kwargs):
    """Returns a custom request body."""
    req_body = {'data': '<DATA>'}
    if 'metadatasize' in kwargs.keys():
        random_data = binascii.b2a_hex(os.urandom(kwargs['metadatasize']))
        req_body['data'] = random_data

    return json.dumps(req_body)


def create_url_from_appender(appender):
    """Returns complete url using the appender (with a  a preceding '/')."""
    next_url = str(CFG.base_server + appender)
    return(next_url)


def get_url_from_location(header):
    """returns : the complete url referring to the location."""
    location = header['location']
    url = create_url_from_appender(location)
    return url


def verify_metadata(get_data, posted_body):
    """TODO(malini) - Really verify the metadata."""
    test_result_flag = False

    get_data = str(get_data)
    posted_body = str(posted_body)
    print(get_data, type(get_data))
    print(posted_body, type(posted_body))

    if get_data in posted_body:
        print('AYYY')
    else:
        test_result_flag = False
        print('NAYYY')

    return test_result_flag


def verify_delete(url, header):
    """Verifies the DELETE was successful, with a GET on the deleted item."""
    test_result_flag = False

    getmsg = http.get(url, header)
    if getmsg.status_code == 404:
        test_result_flag = True
    else:
        print('GET after DELETE failed')
        print('URL')
        print url
        print('headers')
        print header
        print('Response Body')
        print getmsg.text
        assert test_result_flag, 'GET Code {}'.format(getmsg.status_code)

    return test_result_flag

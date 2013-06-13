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
import requests


def get(url, header='', param=''):
    """Does  http GET."""
    if header:
        header = json.loads(header)
    try:
        response = requests.get(url, headers=header, params=param)
    except requests.ConnectionError as detail:
        print("ConnectionError: Exception in http.get {}".format(detail))
    except requests.HTTPError as detail:
        print("HTTPError: Exception in http.get {}".format(detail))
    except requests.Timeout as detail:
        print("Timeout: Exception in http.get {}".format(detail))
    except requests.TooManyRedirects as detail:
        print("TooManyRedirects: Exception in http.get {}".format(detail))
    return response


def post(url, header='', body='', param=''):
    """Does  http POST."""
    if header:
        header = json.loads(header)
    body = str(body)
    body = body.replace("'", '"')
    try:
        response = requests.post(url, headers=header, data=body,
                                 params=param)
    except requests.ConnectionError as detail:
        print("ConnectionError: Exception in http.post {}".format(detail))
    except requests.HTTPError as detail:
        print("HTTPError: Exception in http.post {}".format(detail))
    except requests.Timeout as detail:
        print("Timeout: Exception in http.post {}".format(detail))
    except requests.TooManyRedirects as detail:
        print("TooManyRedirects: Exception in http.post {}".format(detail))
    return response


def put(url, header='', body='', param=''):
    """Does  http PUT."""
    response = None
    if header:
        header = json.loads(header)

    try:
        response = requests.put(url, headers=header, data=body,
                                params=param)
    except requests.ConnectionError as detail:
        print("ConnectionError: Exception in http.put {}".format(detail))
    except requests.HTTPError as detail:
        print("HTTPError: Exception in http.put {}".format(detail))
    except requests.Timeout as detail:
        print("Timeout: Exception in http.put {}".format(detail))
    except requests.TooManyRedirects as detail:
        print("TooManyRedirects: Exception in http.put {}".format(detail))
    return response


def delete(url, header='', param=''):
    """Does  http DELETE."""
    response = None
    if header:
        header = json.loads(header)

    try:
        response = requests.delete(url, headers=header, params=param)
    except requests.ConnectionError as detail:
        print("ConnectionError: Exception in http.delete {}".format(detail))
    except requests.HTTPError as detail:
        print("HTTPError: Exception in http.delete {}".format(detail))
    except requests.Timeout as detail:
        print("Timeout: Exception in http.delete {}".format(detail))
    except requests.TooManyRedirects as detail:
        print("TooManyRedirects: Exception in http.delete {}".format(detail))
    return response


def patch(url, header='', body='', param=''):
    """Does  http PATCH."""
    response = None
    if header:
        header = json.loads(header)

    try:
        response = requests.patch(url, headers=header, data=body,
                                  params=param)
    except requests.ConnectionError as detail:
        print("ConnectionError: Exception in http.patch {}".format(detail))
    except requests.HTTPError as detail:
        print("HTTPError: Exception in http.patch {}".format(detail))
    except requests.Timeout as detail:
        print("Timeout: Exception in http.patch {}".format(detail))
    except requests.TooManyRedirects as detail:
        print("TooManyRedirects: Exception in http.patch {}".format(detail))
    return response


def executetests(row):
    """Entry Point for all tests.

    Executes the tests defined in the *_tests.txt,
    using the test data from *_data.csv.
    """
    http_verb = row['httpverb'].strip()
    url = row['url']
    header = row['header']
    params = row['params']
    body = row['body']
    expected_RC = row['expectedRC']
    expected_RC = int(expected_RC)
    expected_response_body = row['expectedResponseBody']

    response = None

    if http_verb == 'GET':
        response = get(url, header, params)
    elif http_verb == 'POST':
        response = post(url, header, body, params)
    elif http_verb == 'PUT':
        response = put(url, header, body, params)
    elif http_verb == 'DELETE':
        response = delete(url, header, params)
    elif http_verb == 'PATCH':
        response = patch(url, header, body, params)

    if response is not None:
        test_result_flag = verify_response(response, expected_RC)
    else:
        test_result_flag = False

    if test_result_flag:
        return response.headers, response.text
    else:
        print http_verb
        print url
        print header
        print body
        print "Actual Response: {}".format(response.status_code)
        print "Actual Response Headers"
        print response.headers
        print"Actual Response Body"
        print response.text
        print"ExpectedRC: {}".format(expected_RC)
        print"expectedresponsebody: {}".format(expected_response_body)
        assert test_result_flag, "Actual Response does not match the Expected"


def verify_response(response, expected_RC):
    """Compares the http Response code with the expected Response code."""
    test_result_flag = True
    actual_RC = response.status_code
    actual_response_body = response.text

    if actual_RC != expected_RC:
        test_result_flag = False
        print("Unexpected http Response code {}".format(actual_RC))
        print "Response Body returned"
        print actual_response_body

    return test_result_flag

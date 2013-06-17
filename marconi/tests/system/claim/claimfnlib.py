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

from marconi.tests.system.common import functionlib
from marconi.tests.system.common import http


def verify_claim_msg(count, *claim_response):
    """Verifies claim messages.

    Validation steps include - verifying the
    1. number of messages returned is <= limit specified.
    2. query claim & verifying the response.
    :param count: limit specified in the claim request.
    :param claim_response : [header, body] returned for post claim request.
    """
    msg_length_flag = False

    headers = claim_response[0]
    body = claim_response[1]

    msg_length_flag = verify_claim_msglength(count, body)
    if msg_length_flag:
        query_claim(headers, body)
    else:
        assert msg_length_flag, 'More msgs returned than specified in limit'


def verify_claim_msglength(count, *body):
    """Validates that number of messages returned is <= limit specified.

    :param count: value of limit specified in the post claim.
    :param *body: response body returned for the post claim.
    """
    msg_list = body
    msg_list = json.loads(msg_list[0])
    return (len(msg_list) <= count)


def query_claim(headers, *body):
    """Verifies the response of post claim.

    Does a Query Claim using the href in post claim.
    Compares the messages returned in Query claim with the messages
    returned on Post Claim.
    :param headers: headers returned in the post claim response.
    :param *body: message list returned in the post claim response.
    """
    test_result_flag = False

    msg_list = body[0]
    msg_list = json.loads(msg_list)

    location = headers['Location']
    url = functionlib.create_url_from_appender(location)
    header = functionlib.create_marconi_headers()

    get_msg = http.get(url, header)
    if get_msg.status_code == 200:
        query_body = json.loads(get_msg.text)
        query_msgs = query_body['messages']
        test_result_flag = verify_query_msgs(query_msgs, msg_list)

    if test_result_flag:
        return test_result_flag
    else:
        print 'URL'
        print url
        print 'HEADER'
        print header
        print 'Messages returned by Query Claim'
        print query_msgs
        print '# of Messages returned by Query Claim', len(query_msgs)
        print 'Messages returned by Claim Messages'
        print msg_list
        print '# of Messages returned by Claim messages', len(msg_list)
        assert test_result_flag, 'Query Claim Failed'


def verify_query_msgs(querymsgs, msg_list):
    """Verifies response from Query claim.

    Compares the messages returned in Query Claim with the messages
    returned when the claim was posted.
    :param querymsgs: response body returned for Query Claim.
    :param msg_list: message list returned for the original claim.
    """
    test_result_flag = True
    idx = 0

    for msg in querymsgs:
        if ((msg['body'] != msg_list[idx]['body']) or
           (msg['href'] != msg_list[idx]['href']) or
           (msg['ttl'] != msg_list[idx]['ttl'])):
                test_result_flag = False
        idx = idx + 1

    return test_result_flag


def patch_claim(*claim_response):
    """Patches a claim & verifies the results.

    Extracts claim id from the POST response input & updates the claim.
    If PATCH claim succeeds, verifies that the claim TTL is extended.
    :param *claim_response: [headers, body] returned for the original claim
    """
    test_result_flag = False

    headers = claim_response[0]
    location = headers['Location']
    url = functionlib.create_url_from_appender(location)
    header = functionlib.create_marconi_headers()

    ttl_value = 300
    payload = '{"ttl": ttlvalue }'
    payload = payload.replace('ttlvalue', str(ttl_value))

    patch_response = http.patch(url, header, body=payload)
    if patch_response.status_code == 204:
        test_result_flag = verify_patch_claim(url, header, ttl_value)
    else:
        print 'Patch HTTP Response code: {}'.format(patch_response.status_code)
        print patch_response.headers
        print patch_response.text
        assert test_result_flag, 'Patch Claim Failed'

    if not test_result_flag:
        assert test_result_flag, 'Query claim after the patch failed'


def verify_patch_claim(url, header, ttl_extended):
    """Verifies if patch claim was successful.

    The following steps are performed for the verification.
    1. GETs the claim
    2. Checks tht the actual claim TTL value is > TTL in the patch request

    :param ttl_extended : TTL posted in the patch request.
    """
    test_result_flag = True

    get_claim = http.get(url, header)
    response_body = json.loads(get_claim.text)

    ttl = response_body['ttl']
    if ttl < ttl_extended:
        print get_claim.status_code
        print get_claim.headers
        print get_claim.text
        test_result_flag = False

    return test_result_flag


def create_urllist_fromhref(*response):
    """EXtracts href & creates a url list.

    :param *response : http response containing the list of messages.
    """
    rspbody = json.loads(response[1])
    urllist = [functionlib.create_url_from_appender(item['href'])
               for item in rspbody]
    return urllist


def delete_claimed_msgs(*claim_response):
    """Deletes claimed messages.

    Verifies that the deletes were successful with a GET on the deleted msg.
    :param *claim_response: [header, body] returned for post claim request.
    """
    test_result_flag = False

    urllist = create_urllist_fromhref(*claim_response)
    header = functionlib.create_marconi_headers()

    for url in urllist:
        delete_response = http.delete(url, header)
        if delete_response.status_code == 204:
            test_result_flag = functionlib.verify_delete(url, header)
        else:
            print 'DELETE message with claim ID: {}'.format(url)
            print delete_response.status_code
            print delete_response.headers
            print delete_response.text
            assert test_result_flag, 'Delete Claimed Message Failed'

    if not test_result_flag:
        assert test_result_flag, 'Get message after DELETE did not return 404'


def get_claimed_msgs(*claim_response):
    """Does get on all messages returned in the claim.

    :param *claim_response: [header, body] returned for post claim request.
    """
    test_result_flag = True

    urllist = create_urllist_fromhref(*claim_response)
    header = functionlib.create_marconi_headers()

    for url in urllist:
        get_response = http.get(url, header)
        if get_response.status_code != 200:
            print url
            print header
            print 'Get Response Code: {}'.format(get_response.status_code)
            test_result_flag = False

    if not test_result_flag:
        assert test_result_flag, 'Get Claimed message Failed'


def release_claim(*claim_response):
    """Deletes claim & verifies the delete was successful.

    Extracts claim id from the POST response input & deletes the claim.
    If DELETE claim succeeds, verifies that a GET claim returns 404.
    :param *claim_response: [header, body] returned for post claim request.
    """
    test_result_flag = False

    headers = claim_response[0]
    location = headers['Location']
    url = functionlib.create_url_from_appender(location)
    header = functionlib.create_marconi_headers()

    release_response = http.delete(url, header)
    if release_response.status_code == 204:
        test_result_flag = functionlib.verify_delete(url, header)
    else:
        print 'Release Claim HTTP code:{}'.format(release_response.status_code)
        print release_response.headers
        print release_response.text
        assert test_result_flag, 'Release Claim Failed'

    if not test_result_flag:
        assert test_result_flag, 'Get claim after the release failed'

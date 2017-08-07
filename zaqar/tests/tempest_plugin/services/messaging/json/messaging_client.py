# Copyright (c) 2014 Rackspace, Inc.
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

from oslo_utils import uuidutils

from oslo_serialization import jsonutils as json
from six.moves.urllib import parse as urllib
from tempest.lib.common import rest_client

from zaqar.tests.tempest_plugin.api_schema.response.v1 \
    import queues as v1schema
from zaqar.tests.tempest_plugin.api_schema.response.v1_1 \
    import queues as v11schema
from zaqar.tests.tempest_plugin.api_schema.response.v2 \
    import queues as v2schema


class MessagingClient(rest_client.RestClient):

    def __init__(self, auth_provider, service, region, **kwargs):
        super(MessagingClient, self).__init__(
            auth_provider, service, region, **kwargs)

        self.version = '1'
        self.uri_prefix = 'v{0}'.format(self.version)

        client_id = uuidutils.generate_uuid(dashed=False)
        self.headers = {'Client-ID': client_id}


class V1MessagingClient(MessagingClient):
    def __init__(self, auth_provider, service, region, **kwargs):
        super(V1MessagingClient, self).__init__(
            auth_provider, service, region, **kwargs)

        self.version = '1'

    def list_queues(self):
        uri = '{0}/queues'.format(self.uri_prefix)
        resp, body = self.get(uri)

        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v1schema.list_queues, resp, body)
        return resp, body

    def create_queue(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.put(uri, body=None)
        self.expected_success(201, resp.status)
        return resp, body

    def show_queue(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.get(uri)
        self.expected_success(204, resp.status)
        return resp, body

    def head_queue(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.head(uri)
        self.expected_success(204, resp.status)
        return resp, body

    def delete_queue(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.delete(uri)
        self.expected_success(204, resp.status)
        return resp, body

    def show_queue_stats(self, queue_name):
        uri = '{0}/queues/{1}/stats'.format(self.uri_prefix, queue_name)
        resp, body = self.get(uri)
        body = json.loads(body)
        self.validate_response(v1schema.queue_stats, resp, body)
        return resp, body

    def show_queue_metadata(self, queue_name):
        uri = '{0}/queues/{1}/metadata'.format(self.uri_prefix, queue_name)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return resp, body

    def set_queue_metadata(self, queue_name, rbody):
        uri = '{0}/queues/{1}/metadata'.format(self.uri_prefix, queue_name)
        resp, body = self.put(uri, body=json.dumps(rbody))
        self.expected_success(204, resp.status)
        return resp, body

    def post_messages(self, queue_name, rbody):
        uri = '{0}/queues/{1}/messages'.format(self.uri_prefix, queue_name)
        resp, body = self.post(uri, body=json.dumps(rbody),
                               extra_headers=True,
                               headers=self.headers)

        body = json.loads(body)
        self.validate_response(v1schema.post_messages, resp, body)
        return resp, body

    def list_messages(self, queue_name):
        uri = '{0}/queues/{1}/messages?echo=True'.format(self.uri_prefix,
                                                         queue_name)
        resp, body = self.get(uri, extra_headers=True, headers=self.headers)

        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v1schema.list_messages, resp, body)

        return resp, body

    def show_single_message(self, message_uri):
        resp, body = self.get(message_uri, extra_headers=True,
                              headers=self.headers)
        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v1schema.get_single_message, resp,
                                   body)
        return resp, body

    def show_multiple_messages(self, message_uri):
        resp, body = self.get(message_uri, extra_headers=True,
                              headers=self.headers)

        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v1schema.get_multiple_messages,
                                   resp,
                                   body)

        return resp, body

    def delete_messages(self, message_uri):
        resp, body = self.delete(message_uri)
        self.expected_success(204, resp.status)
        return resp, body

    def post_claims(self, queue_name, rbody, url_params=False):
        uri = '{0}/queues/{1}/claims'.format(self.uri_prefix, queue_name)
        if url_params:
            uri += '?%s' % urllib.urlencode(url_params)

        resp, body = self.post(uri, body=json.dumps(rbody),
                               extra_headers=True,
                               headers=self.headers)

        body = json.loads(body)
        self.validate_response(v1schema.claim_messages, resp, body)
        return resp, body

    def query_claim(self, claim_uri):
        resp, body = self.get(claim_uri)

        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v1schema.query_claim, resp, body)
        return resp, body

    def update_claim(self, claim_uri, rbody):
        resp, body = self.patch(claim_uri, body=json.dumps(rbody))
        self.expected_success(204, resp.status)
        return resp, body

    def delete_claim(self, claim_uri):
        resp, body = self.delete(claim_uri)
        self.expected_success(204, resp.status)
        return resp, body


class V11MessagingClient(MessagingClient):
    def __init__(self, auth_provider, service, region, **kwargs):
        super(V11MessagingClient, self).__init__(
            auth_provider, service, region, **kwargs)

        self.version = '1.1'
        self.uri_prefix = 'v{0}'.format(self.version)

    def list_queues(self):
        uri = '{0}/queues'.format(self.uri_prefix)
        resp, body = self.get(uri, headers=self.headers)

        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v11schema.list_queues, resp, body)
        return resp, body

    def create_queue(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.put(uri, body=None, headers=self.headers)
        self.expected_success(201, resp.status)
        return resp, body

    def show_queue(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.get(uri, headers=self.headers)
        self.expected_success(200, resp.status)
        return resp, body

    def delete_queue(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.delete(uri, headers=self.headers)
        self.expected_success(204, resp.status)
        return resp, body

    def show_queue_stats(self, queue_name):
        uri = '{0}/queues/{1}/stats'.format(self.uri_prefix, queue_name)
        resp, body = self.get(uri, headers=self.headers)
        body = json.loads(body)
        self.validate_response(v11schema.queue_stats, resp, body)
        return resp, body

    def show_queue_metadata(self, queue_name):
        uri = '{0}/queues/{1}/metadata'.format(self.uri_prefix, queue_name)
        resp, body = self.get(uri, headers=self.headers)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return resp, body

    def set_queue_metadata(self, queue_name, rbody):
        uri = '{0}/queues/{1}/metadata'.format(self.uri_prefix, queue_name)
        resp, body = self.put(uri, body=json.dumps(rbody),
                              headers=self.headers)
        self.expected_success(204, resp.status)
        return resp, body

    def post_messages(self, queue_name, rbody):
        uri = '{0}/queues/{1}/messages'.format(self.uri_prefix, queue_name)
        resp, body = self.post(uri, body=json.dumps(rbody),
                               extra_headers=True,
                               headers=self.headers)

        body = json.loads(body)
        self.validate_response(v11schema.post_messages, resp, body)
        return resp, body

    def list_messages(self, queue_name):
        uri = '{0}/queues/{1}/messages?echo=True'.format(self.uri_prefix,
                                                         queue_name)
        resp, body = self.get(uri, extra_headers=True, headers=self.headers)

        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v11schema.list_messages, resp, body)

        return resp, body

    def show_single_message(self, message_uri):
        resp, body = self.get(message_uri, extra_headers=True,
                              headers=self.headers)
        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v11schema.get_single_message, resp,
                                   body)
        return resp, body

    def show_multiple_messages(self, message_uri):
        resp, body = self.get(message_uri, extra_headers=True,
                              headers=self.headers)

        if resp['status'] != '404':
            body = json.loads(body)
            self.validate_response(v11schema.get_multiple_messages,
                                   resp,
                                   body)

        return resp, body

    def delete_messages(self, message_uri):
        resp, body = self.delete(message_uri, headers=self.headers)
        self.expected_success(204, resp.status)
        return resp, body

    def post_claims(self, queue_name, rbody, url_params=False):
        uri = '{0}/queues/{1}/claims'.format(self.uri_prefix, queue_name)
        if url_params:
            uri += '?%s' % urllib.urlencode(url_params)

        resp, body = self.post(uri, body=json.dumps(rbody),
                               extra_headers=True,
                               headers=self.headers)

        body = json.loads(body)
        self.validate_response(v11schema.claim_messages, resp, body)
        return resp, body

    def query_claim(self, claim_uri):
        resp, body = self.get(claim_uri, headers=self.headers)

        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v11schema.query_claim, resp, body)
        return resp, body

    def update_claim(self, claim_uri, rbody):
        resp, body = self.patch(claim_uri, body=json.dumps(rbody),
                                headers=self.headers)
        self.expected_success(204, resp.status)
        return resp, body

    def delete_claim(self, claim_uri):
        resp, body = self.delete(claim_uri, headers=self.headers)
        self.expected_success(204, resp.status)
        return resp, body


class V2MessagingClient(MessagingClient):
    def __init__(self, auth_provider, service, region, **kwargs):
        super(V2MessagingClient, self).__init__(
            auth_provider, service, region, **kwargs)

        self.version = '2'
        self.uri_prefix = 'v{0}'.format(self.version)

    def list_queues(self, url_params=False):
        uri = '{0}/queues'.format(self.uri_prefix)
        if url_params:
            uri += '?%s' % urllib.urlencode(url_params)

        resp, body = self.get(uri, headers=self.headers)
        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v2schema.list_queues, resp, body)
        return resp, body

    def create_queue(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.put(uri, body=None, headers=self.headers)
        self.expected_success(201, resp.status)
        return resp, body

    def show_queue(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.get(uri, headers=self.headers)
        self.expected_success(200, resp.status)
        return resp, body

    def delete_queue(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.delete(uri, headers=self.headers)
        self.expected_success(204, resp.status)
        return resp, body

    def purge_queue(self, queue_name, resource=None):
        uri = '{0}/queues/{1}/purge'.format(self.uri_prefix, queue_name)
        rbody = {"resource_types": ["messages", "subscriptions"]}
        if resource:
            rbody = {"resource_types": resource}
        resp, body = self.post(uri, body=json.dumps(rbody),
                               headers=self.headers)
        self.expected_success(204, resp.status)
        return resp, body

    def show_queue_stats(self, queue_name):
        uri = '{0}/queues/{1}/stats'.format(self.uri_prefix, queue_name)
        resp, body = self.get(uri, headers=self.headers)
        body = json.loads(body)
        self.validate_response(v2schema.queue_stats, resp, body)
        return resp, body

    def show_queue_metadata(self, queue_name):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        resp, body = self.get(uri, headers=self.headers)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return resp, body

    def set_queue_metadata(self, queue_name, rbody):
        uri = '{0}/queues/{1}'.format(self.uri_prefix, queue_name)
        headers = self.headers.copy()
        headers['Content-Type'] =\
            'application/openstack-messaging-v2.0-json-patch'
        resp, body = self.patch(uri, body=json.dumps(rbody),
                                headers=headers)
        self.expected_success(200, resp.status)
        return resp, body

    def post_messages(self, queue_name, rbody):
        uri = '{0}/queues/{1}/messages'.format(self.uri_prefix, queue_name)
        resp, body = self.post(uri, body=json.dumps(rbody),
                               extra_headers=True,
                               headers=self.headers)

        body = json.loads(body)
        self.validate_response(v2schema.post_messages, resp, body)
        return resp, body

    def list_messages(self, queue_name):
        uri = '{0}/queues/{1}/messages?echo=True'.format(self.uri_prefix,
                                                         queue_name)
        resp, body = self.get(uri, extra_headers=True, headers=self.headers)

        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v2schema.list_messages, resp, body)

        return resp, body

    def show_single_message(self, message_uri):
        resp, body = self.get(message_uri, extra_headers=True,
                              headers=self.headers)
        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v2schema.get_single_message, resp,
                                   body)
        return resp, body

    def show_multiple_messages(self, message_uri):
        resp, body = self.get(message_uri, extra_headers=True,
                              headers=self.headers)

        if resp['status'] != '404':
            body = json.loads(body)
            self.validate_response(v2schema.get_multiple_messages,
                                   resp,
                                   body)

        return resp, body

    def delete_messages(self, message_uri):
        resp, body = self.delete(message_uri, headers=self.headers)
        self.expected_success(204, resp.status)
        return resp, body

    def post_claims(self, queue_name, rbody, url_params=False):
        uri = '{0}/queues/{1}/claims'.format(self.uri_prefix, queue_name)
        if url_params:
            uri += '?%s' % urllib.urlencode(url_params)

        resp, body = self.post(uri, body=json.dumps(rbody),
                               extra_headers=True,
                               headers=self.headers)

        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v2schema.claim_messages, resp, body)
        return resp, body

    def query_claim(self, claim_uri):
        resp, body = self.get(claim_uri, headers=self.headers)

        if resp['status'] != '204':
            body = json.loads(body)
            self.validate_response(v2schema.query_claim, resp, body)
        return resp, body

    def update_claim(self, claim_uri, rbody):
        resp, body = self.patch(claim_uri, body=json.dumps(rbody),
                                headers=self.headers)
        self.expected_success(204, resp.status)
        return resp, body

    def delete_claim(self, claim_uri):
        resp, body = self.delete(claim_uri, headers=self.headers)
        self.expected_success(204, resp.status)
        return resp, body

    def create_subscription(self, queue_name, rbody):
        uri = '{0}/queues/{1}/subscriptions'.format(self.uri_prefix,
                                                    queue_name)

        resp, body = self.post(uri, body=json.dumps(rbody),
                               extra_headers=True,
                               headers=self.headers)
        body = json.loads(body)
        self.validate_response(v2schema.create_subscription, resp, body)
        return resp, body

    def delete_subscription(self, queue_name, subscription_id):
        uri = '{0}/queues/{1}/subscriptions/{2}'.format(self.uri_prefix,
                                                        queue_name,
                                                        subscription_id)
        resp, body = self.delete(uri, headers=self.headers)
        return resp, body

    def list_subscription(self, queue_name):
        uri = '{0}/queues/{1}/subscriptions/'.format(self.uri_prefix,
                                                     queue_name)
        resp, body = self.get(uri, headers=self.headers)
        body = json.loads(body)
        self.validate_response(v2schema.list_subscriptions, resp, body)
        return resp, body

    def show_subscription(self, queue_name, subscription_id):
        uri = '{0}/queues/{1}/subscriptions/{2}'.format(self.uri_prefix,
                                                        queue_name,
                                                        subscription_id)
        resp, body = self.get(uri, headers=self.headers)
        body = json.loads(body)
        self.validate_response(v2schema.show_single_subscription, resp, body)
        return resp, body

    def update_subscription(self, queue_name, subscription_id, rbody):
        uri = '{0}/queues/{1}/subscriptions/{2}'.format(self.uri_prefix,
                                                        queue_name,
                                                        subscription_id)
        resp, body = self.patch(uri, body=json.dumps(rbody),
                                headers=self.headers)
        return resp, body

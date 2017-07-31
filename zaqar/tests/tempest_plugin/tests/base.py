# Copyright (c) 2016 HuaWei, Inc.
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

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest import test

from zaqar.tests.tempest_plugin.services.messaging.json import messaging_client

CONF = config.CONF


class BaseMessagingTest(test.BaseTestCase):

    """Base class for the Messaging (Zaqar) tests

    It is assumed that the following option is defined in the
    [service_available] section of etc/tempest.conf

        messaging as True
    """

    credentials = ['primary']

    @classmethod
    def skip_checks(cls):
        super(BaseMessagingTest, cls).skip_checks()
        if not CONF.service_available.zaqar:
            raise cls.skipException("Zaqar support is required")

    @classmethod
    def resource_setup(cls):
        super(BaseMessagingTest, cls).resource_setup()
        cls.messaging_cfg = CONF.messaging

    @classmethod
    def create_queue(cls, queue_name):
        """Wrapper utility that returns a test queue."""
        resp, body = cls.client.create_queue(queue_name)
        return resp, body

    @classmethod
    def delete_queue(cls, queue_name):
        """Wrapper utility that deletes a test queue."""
        resp, body = cls.client.delete_queue(queue_name)
        return resp, body

    @classmethod
    def list_queues(cls):
        """Wrapper utility that lists queues."""
        resp, body = cls.client.list_queues()
        return resp, body

    @classmethod
    def get_queue_stats(cls, queue_name):
        """Wrapper utility that returns the queue stats."""
        resp, body = cls.client.show_queue_stats(queue_name)
        return resp, body

    @classmethod
    def get_queue_metadata(cls, queue_name):
        """Wrapper utility that gets a queue metadata."""
        resp, body = cls.client.show_queue_metadata(queue_name)
        return resp, body

    @classmethod
    def set_queue_metadata(cls, queue_name, rbody):
        """Wrapper utility that sets the metadata of a queue."""
        resp, body = cls.client.set_queue_metadata(queue_name, rbody)
        return resp, body

    @classmethod
    def post_messages(cls, queue_name, rbody):
        """Wrapper utility that posts messages to a queue."""
        resp, body = cls.client.post_messages(queue_name, rbody)

        return resp, body

    @classmethod
    def list_messages(cls, queue_name):
        """Wrapper utility that lists the messages in a queue."""
        resp, body = cls.client.list_messages(queue_name)

        return resp, body

    @classmethod
    def delete_messages(cls, message_uri):
        """Wrapper utility that deletes messages."""
        resp, body = cls.client.delete_messages(message_uri)

        return resp, body

    @classmethod
    def post_claims(cls, queue_name, rbody, url_params=False):
        """Wrapper utility that claims messages."""
        resp, body = cls.client.post_claims(
            queue_name, rbody, url_params=False)

        return resp, body

    @classmethod
    def query_claim(cls, claim_uri):
        """Wrapper utility that gets a claim."""
        resp, body = cls.client.query_claim(claim_uri)

        return resp, body

    @classmethod
    def update_claim(cls, claim_uri, rbody):
        """Wrapper utility that updates a claim."""
        resp, body = cls.client.update_claim(claim_uri, rbody)

        return resp, body

    @classmethod
    def release_claim(cls, claim_uri):
        """Wrapper utility that deletes a claim."""
        resp, body = cls.client.delete_claim(claim_uri)

        return resp, body

    @classmethod
    def generate_message_body(cls, repeat=1):
        """Wrapper utility that sets the metadata of a queue."""
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)

        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        message_body = {key: value}

        rbody = ([{'body': message_body, 'ttl': message_ttl}] * repeat)
        return rbody


class BaseV1MessagingTest(BaseMessagingTest):
    """Base class for the Messaging (Zaqar) v1.0 tests."""
    @classmethod
    def setup_clients(cls):
        super(BaseV1MessagingTest, cls).setup_clients()
        cls.client = messaging_client.V1MessagingClient(
            cls.os_primary.auth_provider,
            CONF.messaging.catalog_type,
            CONF.identity.region,
            build_interval=CONF.compute.build_interval,
            build_timeout=CONF.compute.build_timeout)

    @classmethod
    def check_queue_exists(cls, queue_name):
        """Wrapper utility that checks the existence of a test queue."""
        resp, body = cls.client.show_queue(queue_name)
        return resp, body

    @classmethod
    def check_queue_exists_head(cls, queue_name):
        """Wrapper utility checks the head of a queue via http HEAD."""
        resp, body = cls.client.head_queue(queue_name)
        return resp, body


class BaseV11MessagingTest(BaseMessagingTest):
    """Base class for the Messaging (Zaqar) v1.1 tests."""
    @classmethod
    def setup_clients(cls):
        super(BaseV11MessagingTest, cls).setup_clients()
        cls.client = messaging_client.V11MessagingClient(
            cls.os_primary.auth_provider,
            CONF.messaging.catalog_type,
            CONF.identity.region,
            build_interval=CONF.compute.build_interval,
            build_timeout=CONF.compute.build_timeout)

    @classmethod
    def generate_message_body(cls, repeat=1):
        """Wrapper utility that sets the metadata of a queue."""
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)

        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        message_body = {key: value}

        body = ([{'body': message_body, 'ttl': message_ttl}] * repeat)
        rbody = {'messages': body}
        return rbody


class BaseV2MessagingTest(BaseMessagingTest):
    """Base class for the Messaging (Zaqar) v2 tests."""
    @classmethod
    def setup_clients(cls):
        super(BaseV2MessagingTest, cls).setup_clients()
        cls.client = messaging_client.V2MessagingClient(
            cls.os_primary.auth_provider,
            CONF.messaging.catalog_type,
            CONF.identity.region,
            build_interval=CONF.compute.build_interval,
            build_timeout=CONF.compute.build_timeout)

    @classmethod
    def purge_queue(cls, queue_name, resource=None):
        resp, body = cls.client.purge_queue(
            queue_name, resource)
        return resp, body

    @classmethod
    def create_subscription(cls, queue_name, rbody):
        resp, body = cls.client.create_subscription(
            queue_name, rbody)
        return resp, body

    @classmethod
    def delete_subscription(cls, queue_name, subscription_id):
        resp, body = cls.client.delete_subscription(queue_name,
                                                    subscription_id)
        return resp, body

    @classmethod
    def list_subscription(cls, queue_name):
        resp, body = cls.client.list_subscription(queue_name)
        return resp, body

    @classmethod
    def show_subscription(cls, queue_name, subscription_id):
        resp, body = cls.client.show_subscription(queue_name, subscription_id)
        return resp, body

    @classmethod
    def update_subscription(cls, queue_name, subscription_id, rbody):
        resp, body = cls.client.update_subscription(queue_name,
                                                    subscription_id,
                                                    rbody)
        return resp, body

    @classmethod
    def generate_subscription_body(cls):
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)

        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        option_body = {key: value}
        subscribers = ['http://fake:8080', 'https://fake:8080',
                       'mailto:fake@123.com']
        rbody = [{'options': option_body, 'ttl': message_ttl,
                  'subscriber': subscriber} for subscriber in subscribers]
        return rbody

    @classmethod
    def generate_message_body(cls, repeat=1):
        """Wrapper utility that sets the metadata of a queue."""
        message_ttl = data_utils.\
            rand_int_id(start=60, end=CONF.messaging.max_message_ttl)

        key = data_utils.arbitrary_string(size=20, base_text='MessagingKey')
        value = data_utils.arbitrary_string(size=20,
                                            base_text='MessagingValue')
        message_body = {key: value}

        body = ([{'body': message_body, 'ttl': message_ttl}] * repeat)
        rbody = {'messages': body}
        return rbody

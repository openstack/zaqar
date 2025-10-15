# Copyright (c) 2014 Prashanth Raghu.
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

import collections
import time
from unittest import mock
import uuid

from oslo_utils import timeutils
from oslo_utils import uuidutils
import redis

from zaqar.common import cache as oslo_cache
from zaqar.common import errors
from zaqar.conf import drivers_message_store_redis
from zaqar import storage
from zaqar.storage import pooling
from zaqar.storage.redis import controllers
from zaqar.storage.redis import driver
from zaqar.storage.redis import messages
from zaqar.storage.redis import utils
from zaqar import tests as testing
from zaqar.tests.unit.storage import base


def _create_sample_message(now=None, claimed=False, body=None):
    if now is None:
        now = timeutils.utcnow_ts()

    if claimed:
        claim_id = uuid.uuid4()
        claim_expires = now + 300
    else:
        claim_id = None
        claim_expires = now

    if body is None:
        body = {}

    return messages.Message(
        ttl=60,
        created=now,
        client_uuid=uuid.uuid4(),
        claim_id=claim_id,
        claim_expires=claim_expires,
        body=body
    )


class RedisUtilsTest(testing.TestBase):

    config_file = 'wsgi_redis.conf'

    def setUp(self):
        super().setUp()

        self.conf.register_opts(drivers_message_store_redis.ALL_OPTS,
                                group=drivers_message_store_redis.GROUP_NAME)

        self.redis_conf = self.conf[drivers_message_store_redis.GROUP_NAME]

        MockDriver = collections.namedtuple('MockDriver', 'redis_conf')

        self.driver = MockDriver(self.redis_conf)

    def test_scope_queue_name(self):
        self.assertEqual('.my-q', utils.scope_queue_name('my-q'))
        self.assertEqual('.my-q', utils.scope_queue_name('my-q', None))
        self.assertEqual('123.my-q', utils.scope_queue_name('my-q', '123'))
        self.assertEqual('123.my-q_1', utils.scope_queue_name('my-q_1', '123'))

        self.assertEqual('.', utils.scope_queue_name())
        self.assertEqual('123.', utils.scope_queue_name(None, '123'))

    def test_scope_messages_set(self):
        self.assertEqual('.my-q.', utils.scope_message_ids_set('my-q'))
        self.assertEqual('p.my-q.', utils.scope_message_ids_set('my-q', 'p'))
        self.assertEqual('p.my-q.s',
                         utils.scope_message_ids_set('my-q', 'p', 's'))

        self.assertEqual('..', utils.scope_message_ids_set(None))
        self.assertEqual('123..', utils.scope_message_ids_set(None, '123'))
        self.assertEqual('..s', utils.scope_message_ids_set(None, None, 's'))

    def test_descope_messages_set(self):
        key = utils.scope_message_ids_set('my-q')
        self.assertEqual(('my-q', None), utils.descope_message_ids_set(key))

        key = utils.scope_message_ids_set('my-q', '123')
        self.assertEqual(('my-q', '123'), utils.descope_message_ids_set(key))

        key = utils.scope_message_ids_set(None, '123')
        self.assertEqual((None, '123'), utils.descope_message_ids_set(key))

        key = utils.scope_message_ids_set()
        self.assertEqual((None, None), utils.descope_message_ids_set(key))

    def test_normalize_none_str(self):

        self.assertEqual('my-q', utils.normalize_none_str('my-q'))
        self.assertEqual('', utils.normalize_none_str(None))

    def test_msg_claimed_filter(self):
        now = timeutils.utcnow_ts()

        unclaimed_msg = _create_sample_message()
        self.assertFalse(utils.msg_claimed_filter(unclaimed_msg, now))

        claimed_msg = _create_sample_message(claimed=True)
        self.assertTrue(utils.msg_claimed_filter(claimed_msg, now))

        # NOTE(kgriffs): Has a claim ID, but the claim is expired
        claimed_msg.claim_expires = now - 60
        self.assertFalse(utils.msg_claimed_filter(claimed_msg, now))

    def test_descope_queue_name(self):
        self.assertEqual('q', utils.descope_queue_name('p.q'))
        self.assertEqual('q', utils.descope_queue_name('.q'))
        self.assertEqual('', utils.descope_queue_name('.'))

    def test_msg_echo_filter(self):
        msg = _create_sample_message()
        self.assertTrue(utils.msg_echo_filter(msg, msg.client_uuid))

        alt_uuid = uuidutils.generate_uuid()
        self.assertFalse(utils.msg_echo_filter(msg, alt_uuid))

    def test_basic_message(self):
        now = timeutils.utcnow_ts()
        body = {
            'msg': 'Hello Earthlings!',
            'unicode': 'ab\u00e7',
            'bytes': b'ab\xc3\xa7',
            b'ab\xc3\xa7': 'one, two, three',
            'ab\u00e7': 'one, two, three',
        }

        msg = _create_sample_message(now=now, body=body)
        basic_msg = msg.to_basic(now + 5)

        self.assertEqual(msg.id, basic_msg['id'])
        self.assertEqual(5, basic_msg['age'])
        self.assertEqual(body, basic_msg['body'])
        self.assertEqual(msg.ttl, basic_msg['ttl'])

    def test_retries_on_connection_error(self):
        num_calls = [0]

        @utils.retries_on_connection_error
        def _raises_connection_error(self):
            num_calls[0] += 1
            raise redis.exceptions.ConnectionError

        self.assertRaises(redis.exceptions.ConnectionError,
                          _raises_connection_error, self)
        self.assertEqual([self.redis_conf.max_reconnect_attempts], num_calls)


@testing.requires_redis
class RedisDriverTest(testing.TestBase):

    config_file = 'wsgi_redis.conf'

    def test_db_instance(self):
        oslo_cache.register_config(self.conf)
        cache = oslo_cache.get_cache(self.conf)
        redis_driver = driver.DataDriver(self.conf, cache,
                                         driver.ControlDriver
                                         (self.conf, cache))

        self.assertIsInstance(redis_driver.connection, redis.Redis)

    def test_version_match(self):
        oslo_cache.register_config(self.conf)
        cache = oslo_cache.get_cache(self.conf)

        with mock.patch('redis.Redis.info') as info:
            info.return_value = {'redis_version': '2.4.6'}
            self.assertRaises(RuntimeError, driver.DataDriver,
                              self.conf, cache,
                              driver.ControlDriver(self.conf, cache))

            info.return_value = {'redis_version': '2.11'}

            try:
                driver.DataDriver(self.conf, cache,
                                  driver.ControlDriver(self.conf, cache))
            except RuntimeError:
                self.fail('version match failed')

    def test_connection_url_invalid(self):
        self.assertRaises(errors.ConfigurationError,
                          driver.ConnectionURI,
                          'red://example.com')

        self.assertRaises(errors.ConfigurationError,
                          driver.ConnectionURI,
                          'redis://')

        self.assertRaises(errors.ConfigurationError,
                          driver.ConnectionURI,
                          'redis://example.com:not_an_integer')

        self.assertRaises(errors.ConfigurationError,
                          driver.ConnectionURI,
                          'redis://s1:not_an_integer,s2?master=obi-wan')

        self.assertRaises(errors.ConfigurationError,
                          driver.ConnectionURI,
                          'redis://s1,s2')

        self.assertRaises(errors.ConfigurationError,
                          driver.ConnectionURI,
                          'redis:')

        self.assertRaises(errors.ConfigurationError,
                          driver.ConnectionURI,
                          'redis:')

    def test_connection_url_tcp(self):
        uri = driver.ConnectionURI('redis://example.com')
        self.assertEqual(driver.STRATEGY_TCP, uri.strategy)
        self.assertEqual(6379, uri.port)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertIsNone(uri.password)

        uri = driver.ConnectionURI('redis://example.com:7777')
        self.assertEqual(driver.STRATEGY_TCP, uri.strategy)
        self.assertEqual(7777, uri.port)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertIsNone(uri.password)

        uri = driver.ConnectionURI(
            'redis://example.com:7777?socket_timeout=1')
        self.assertEqual(driver.STRATEGY_TCP, uri.strategy)
        self.assertEqual(7777, uri.port)
        self.assertEqual(1.0, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertIsNone(uri.password)

        uri = driver.ConnectionURI(
            'redis://:test123@example.com:7777?socket_timeout=1&dbid=5')
        self.assertEqual(driver.STRATEGY_TCP, uri.strategy)
        self.assertEqual(7777, uri.port)
        self.assertEqual(1.0, uri.socket_timeout)
        self.assertEqual(5, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertEqual('test123', uri.password)

        self.assertRaises(
            errors.ConfigurationError,
            driver.ConnectionURI, 'redis://test123@example.com')

        uri = driver.ConnectionURI(
            'redis://default:test123@example.com')
        self.assertEqual(driver.STRATEGY_TCP, uri.strategy)
        self.assertEqual(6379, uri.port)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertEqual('default', uri.username)
        self.assertEqual('test123', uri.password)

    def test_connection_uri_unix_socket(self):
        uri = driver.ConnectionURI('redis:///tmp/redis.sock')
        self.assertEqual(driver.STRATEGY_UNIX, uri.strategy)
        self.assertEqual('/tmp/redis.sock', uri.unix_socket_path)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertIsNone(uri.password)

        uri = driver.ConnectionURI(
            'redis:///tmp/redis.sock?socket_timeout=1.5')
        self.assertEqual(driver.STRATEGY_UNIX, uri.strategy)
        self.assertEqual('/tmp/redis.sock', uri.unix_socket_path)
        self.assertEqual(1.5, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertIsNone(uri.password)

        uri = driver.ConnectionURI(
            'redis://:test123@/tmp/redis.sock?'
            'socket_timeout=1.5&dbid=5')
        self.assertEqual(driver.STRATEGY_UNIX, uri.strategy)
        self.assertEqual('/tmp/redis.sock', uri.unix_socket_path)
        self.assertEqual(1.5, uri.socket_timeout)
        self.assertEqual(5, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertEqual('test123', uri.password)

        # NOTE(tkajinam): Test fallback for backword compatibility
        uri = driver.ConnectionURI(
            'redis://test123@/tmp/redis.sock')
        self.assertEqual(driver.STRATEGY_UNIX, uri.strategy)
        self.assertEqual('/tmp/redis.sock', uri.unix_socket_path)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertEqual('test123', uri.password)

        uri = driver.ConnectionURI(
            'redis://default:test123@/tmp/redis.sock')
        self.assertEqual(driver.STRATEGY_UNIX, uri.strategy)
        self.assertEqual('/tmp/redis.sock', uri.unix_socket_path)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertEqual('default', uri.username)
        self.assertEqual('test123', uri.password)

    def test_connection_uri_sentinel(self):
        uri = driver.ConnectionURI('redis://s1?master=dumbledore')
        self.assertEqual(driver.STRATEGY_SENTINEL, uri.strategy)
        self.assertEqual([('s1', 26379)], uri.sentinels)
        self.assertEqual('dumbledore', uri.master)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertIsNone(uri.password)
        self.assertIsNone(uri.sentinel_username)
        self.assertIsNone(uri.sentinel_password)

        uri = driver.ConnectionURI('redis://s1,s2?master=dumbledore')
        self.assertEqual(driver.STRATEGY_SENTINEL, uri.strategy)
        self.assertEqual([('s1', 26379), ('s2', 26379)], uri.sentinels)
        self.assertEqual('dumbledore', uri.master)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertIsNone(uri.password)
        self.assertIsNone(uri.sentinel_username)
        self.assertIsNone(uri.sentinel_password)

        uri = driver.ConnectionURI('redis://s1:26389,s1?master=dumbledore')
        self.assertEqual(driver.STRATEGY_SENTINEL, uri.strategy)
        self.assertEqual([('s1', 26389), ('s1', 26379)], uri.sentinels)
        self.assertEqual('dumbledore', uri.master)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertIsNone(uri.password)
        self.assertIsNone(uri.sentinel_username)
        self.assertIsNone(uri.sentinel_password)

        uri = driver.ConnectionURI(
            'redis://[::1]:26389,[::2]?master=dumbledore')
        self.assertEqual(driver.STRATEGY_SENTINEL, uri.strategy)
        self.assertEqual([('::1', 26389), ('::2', 26379)], uri.sentinels)
        self.assertEqual('dumbledore', uri.master)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertIsNone(uri.password)
        self.assertIsNone(uri.sentinel_username)
        self.assertIsNone(uri.sentinel_password)

        uri = driver.ConnectionURI(
            'redis://s1?master=dumbledore&socket_timeout=0.5')
        self.assertEqual(driver.STRATEGY_SENTINEL, uri.strategy)
        self.assertEqual([('s1', 26379)], uri.sentinels)
        self.assertEqual('dumbledore', uri.master)
        self.assertEqual(0.5, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertIsNone(uri.password)
        self.assertIsNone(uri.sentinel_username)
        self.assertIsNone(uri.sentinel_password)

        uri = driver.ConnectionURI(
            'redis://:test123@s1?master=dumbledore&socket_timeout=0.5&dbid=5')
        self.assertEqual(driver.STRATEGY_SENTINEL, uri.strategy)
        self.assertEqual([('s1', 26379)], uri.sentinels)
        self.assertEqual('dumbledore', uri.master)
        self.assertEqual(0.5, uri.socket_timeout)
        self.assertEqual(5, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertEqual('test123', uri.password)
        self.assertIsNone(uri.sentinel_username)
        self.assertIsNone(uri.sentinel_password)

        # NOTE(tkajinam): Test fallback for backword compatibility
        uri = driver.ConnectionURI(
            'redis://test123@s1?master=dumbledore')
        self.assertEqual(driver.STRATEGY_SENTINEL, uri.strategy)
        self.assertEqual([('s1', 26379)], uri.sentinels)
        self.assertEqual('dumbledore', uri.master)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertIsNone(uri.username)
        self.assertEqual('test123', uri.password)
        self.assertIsNone(uri.sentinel_username)
        self.assertIsNone(uri.sentinel_password)

        uri = driver.ConnectionURI(
            'redis://default:test123@s1?master=dumbledore')
        self.assertEqual(driver.STRATEGY_SENTINEL, uri.strategy)
        self.assertEqual([('s1', 26379)], uri.sentinels)
        self.assertEqual('dumbledore', uri.master)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertEqual('default', uri.username)
        self.assertEqual('test123', uri.password)
        self.assertIsNone(uri.sentinel_username)
        self.assertIsNone(uri.sentinel_password)

        uri = driver.ConnectionURI(
            'redis://default:test123@s1?master=dumbledore'
            '&sentinel_username=sentinel&sentinel_password=test456')
        self.assertEqual(driver.STRATEGY_SENTINEL, uri.strategy)
        self.assertEqual([('s1', 26379)], uri.sentinels)
        self.assertEqual('dumbledore', uri.master)
        self.assertEqual(0.1, uri.socket_timeout)
        self.assertEqual(0, uri.dbid)
        self.assertEqual('default', uri.username)
        self.assertEqual('test123', uri.password)
        self.assertEqual('sentinel', uri.sentinel_username)
        self.assertEqual('test456', uri.sentinel_password)


@testing.requires_redis
class RedisQueuesTest(base.QueueControllerTest):

    driver_class = driver.DataDriver
    config_file = 'wsgi_redis.conf'
    controller_class = controllers.QueueController
    control_driver_class = driver.ControlDriver

    def setUp(self):
        super().setUp()
        self.connection = self.driver.connection
        self.msg_controller = self.driver.message_controller

    def tearDown(self):
        super().tearDown()
        self.connection.flushdb()


@testing.requires_redis
class RedisMessagesTest(base.MessageControllerTest):
    driver_class = driver.DataDriver
    config_file = 'wsgi_redis.conf'
    controller_class = controllers.MessageController
    control_driver_class = driver.ControlDriver
    gc_interval = 1

    def setUp(self):
        super().setUp()
        self.connection = self.driver.connection

    def tearDown(self):
        super().tearDown()
        self.connection.flushdb()

    def test_count(self):
        queue_name = 'get-count'
        self.queue_controller.create(queue_name)

        msgs = [{
            'ttl': 300,
            'body': 'di mo fy'
        } for i in range(0, 10)]

        client_id = uuid.uuid4()
        # Creating 10 messages
        self.controller.post(queue_name, msgs, client_id)

        num_msg = self.controller._count(queue_name, None)
        self.assertEqual(10, num_msg)

    def test_empty_queue_exception(self):
        queue_name = 'empty-queue-test'
        self.queue_controller.create(queue_name)

        self.assertRaises(storage.errors.QueueIsEmpty,
                          self.controller.first, queue_name)

    def test_gc(self):
        self.queue_controller.create(self.queue_name)
        self.controller.post(self.queue_name,
                             [{'ttl': 0, 'body': {}}],
                             client_uuid=uuidutils.generate_uuid())

        num_removed = self.controller.gc()
        self.assertEqual(1, num_removed)

        for _ in range(100):
            self.controller.post(self.queue_name,
                                 [{'ttl': 0, 'body': {}}],
                                 client_uuid=uuidutils.generate_uuid())

        num_removed = self.controller.gc()
        self.assertEqual(100, num_removed)

    def test_invalid_uuid(self):
        queue_name = 'invalid-uuid-test'
        msgs = [{
            'ttl': 300,
            'body': 'di mo fy'
        }]
        client_id = "invalid_uuid"
        self.assertRaises(ValueError, self.controller.post, queue_name, msgs,
                          client_id)


@testing.requires_redis
class RedisClaimsTest(base.ClaimControllerTest):
    driver_class = driver.DataDriver
    config_file = 'wsgi_redis.conf'
    controller_class = controllers.ClaimController
    control_driver_class = driver.ControlDriver

    def setUp(self):
        super().setUp()
        self.connection = self.driver.connection

    def tearDown(self):
        super().tearDown()
        self.connection.flushdb()

    def test_claim_doesnt_exist(self):
        queue_name = 'no-such-claim'
        epoch = '000000000000000000000000'
        self.queue_controller.create(queue_name)
        self.assertRaises(storage.errors.ClaimDoesNotExist,
                          self.controller.get, queue_name,
                          epoch, project=None)

        claim_id, messages = self.controller.create(queue_name, {'ttl': 1,
                                                    'grace': 0},
                                                    project=None)

        # Lets let it expire
        time.sleep(1)
        self.assertRaises(storage.errors.ClaimDoesNotExist,
                          self.controller.update, queue_name,
                          claim_id, {}, project=None)

        # create a claim and then delete the queue
        claim_id, messages = self.controller.create(queue_name, {'ttl': 100,
                                                    'grace': 0},
                                                    project=None)
        self.queue_controller.delete(queue_name)

        self.assertRaises(storage.errors.ClaimDoesNotExist,
                          self.controller.get, queue_name,
                          claim_id, project=None)

        self.assertRaises(storage.errors.ClaimDoesNotExist,
                          self.controller.update, queue_name,
                          claim_id, {}, project=None)

    def test_get_claim_after_expires(self):
        queue_name = 'no-such-claim'
        self.queue_controller.create(queue_name, project='fake_project')
        new_messages = [{'ttl': 60, 'body': {}},
                        {'ttl': 60, 'body': {}},
                        {'ttl': 60, 'body': {}}]
        self.message_controller.post(queue_name, new_messages,
                                     client_uuid=str(uuid.uuid4()),
                                     project='fake_project')
        claim_id, messages = self.controller.create(queue_name, {'ttl': 1,
                                                    'grace': 0},
                                                    project='fake_project')
        # Lets let it expire
        time.sleep(2)
        self.assertRaises(storage.errors.ClaimDoesNotExist,
                          self.controller.get, queue_name,
                          claim_id, project='fake_project')

    def test_gc(self):
        self.queue_controller.create(self.queue_name)

        for _ in range(100):
            self.message_controller.post(self.queue_name,
                                         [{'ttl': 300, 'body': 'yo gabba'}],
                                         client_uuid=uuidutils.generate_uuid())

        now = timeutils.utcnow_ts()
        timeutils_utcnow = 'oslo_utils.timeutils.utcnow_ts'

        # Test a single claim
        with mock.patch(timeutils_utcnow) as mock_utcnow:
            mock_utcnow.return_value = now - 1
            self.controller.create(self.queue_name, {'ttl': 1, 'grace': 60})

        num_removed = self.controller._gc(self.queue_name, None)
        self.assertEqual(1, num_removed)

        # Test multiple claims
        with mock.patch(timeutils_utcnow) as mock_utcnow:
            mock_utcnow.return_value = now - 1

            for _ in range(5):
                self.controller.create(self.queue_name,
                                       {'ttl': 1, 'grace': 60})

        # NOTE(kgriffs): These ones should not be cleaned up
        self.controller.create(self.queue_name, {'ttl': 60, 'grace': 60})
        self.controller.create(self.queue_name, {'ttl': 60, 'grace': 60})

        num_removed = self.controller._gc(self.queue_name, None)
        self.assertEqual(5, num_removed)


@testing.requires_redis
class RedisSubscriptionTests(base.SubscriptionControllerTest):
    driver_class = driver.DataDriver
    config_file = 'wsgi_redis.conf'
    controller_class = controllers.SubscriptionController
    control_driver_class = driver.ControlDriver


@testing.requires_redis
class RedisPoolsTests(base.PoolsControllerTest):
    config_file = 'wsgi_redis.conf'
    driver_class = driver.ControlDriver
    controller_class = controllers.PoolsController
    control_driver_class = driver.ControlDriver

    def setUp(self):
        super().setUp()
        self.pools_controller = self.driver.pools_controller
        # Let's create one pool
        self.pool = str(uuid.uuid1())
        self.pools_controller.create(self.pool, 100, 'localhost', options={})
        self.pool1 = str(uuid.uuid1())
        self.flavor = str(uuid.uuid1())
        self.flavors_controller.create(self.flavor,
                                       project=self.project,
                                       capabilities={})
        self.pools_controller.create(self.pool1, 100, 'localhost1',
                                     flavor=self.flavor, options={})
        self.flavors_controller = self.driver.flavors_controller

    def tearDown(self):
        self.pools_controller.drop_all()
        super().tearDown()

    def test_delete_pool_used_by_flavor(self):
        with testing.expect(storage.errors.PoolInUseByFlavor):
            self.pools_controller.delete(self.pool1)

    def test_mismatching_capabilities_fifo(self):
        # NOTE(gengchc2): The fifo function is not implemented
        # in redis, we skip it.
        self.skip("The fifo function is not implemented")

    def test_mismatching_capabilities1(self):
        # NOTE(gengchc2): This test is used for testing mismatchming
        # capabilities in pool with flavor
        with testing.expect(storage.errors.PoolCapabilitiesMismatch):
            self.pools_controller.create(str(uuid.uuid1()),
                                         100, 'mongodb://localhost',
                                         flavor=self.flavor,
                                         options={})


@testing.requires_redis
class RedisCatalogueTests(base.CatalogueControllerTest):
    driver_class = driver.ControlDriver
    controller_class = controllers.CatalogueController
    control_driver_class = driver.ControlDriver
    config_file = 'wsgi_redis.conf'

    def setUp(self):
        super().setUp()
        self.addCleanup(self.controller.drop_all)


@testing.requires_redis
class PooledMessageTests(base.MessageControllerTest):
    config_file = 'wsgi_redis_pooled.conf'
    controller_class = pooling.MessageController
    driver_class = pooling.DataDriver
    control_driver_class = driver.ControlDriver
    controller_base_class = storage.Message

    # NOTE(kgriffs): Redis's TTL scavenger only runs once a minute
    gc_interval = 60


@testing.requires_redis
class PooledClaimsTests(base.ClaimControllerTest):
    config_file = 'wsgi_redis_pooled.conf'
    controller_class = pooling.ClaimController
    driver_class = pooling.DataDriver
    control_driver_class = driver.ControlDriver
    controller_base_class = storage.Claim

    def setUp(self):
        super().setUp()
        self.connection = self.controller._pool_catalog.lookup(
            self.queue_name, self.project)._storage.\
            claim_controller.driver.connection

    def tearDown(self):
        super().tearDown()
        self.connection.flushdb()


# NOTE(gengchc2): Unittest for new flavor configure scenario.
@testing.requires_redis
class RedisFlavorsTest1(base.FlavorsControllerTest1):
    driver_class = driver.ControlDriver
    controller_class = controllers.FlavorsController
    control_driver_class = driver.ControlDriver
    config_file = 'wsgi_redis.conf'

    def setUp(self):
        super().setUp()
        self.addCleanup(self.controller.drop_all)

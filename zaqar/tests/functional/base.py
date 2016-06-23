# Copyright (c) 2013 Rackspace, Inc.
# Copyright (c) 2013 Red Hat, Inc.
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

import abc
import multiprocessing
import os

import jsonschema
from oslo_utils import timeutils
import six

from zaqar.api.v1 import response as response_v1
from zaqar.api.v1_1 import response as response_v1_1
from zaqar.api.v2 import response as response_v2
from zaqar import bootstrap
from zaqar.storage import mongodb
from zaqar.storage.redis import driver as redis
from zaqar import tests as testing
from zaqar.tests.functional import config
from zaqar.tests.functional import helpers
from zaqar.tests.functional import http
from zaqar.tests import helpers as base_helpers
from zaqar.transport import base as transport_base
# TODO(flaper87): This is necessary to register,
# wsgi configs and won't be permanent. It'll be
# refactored as part of the work for this blueprint
from zaqar.transport import validation
from zaqar.transport import wsgi  # noqa

# TODO(kgriffs): Run functional tests to a devstack gate job and
# set this using an environment variable or something.
#
# TODO(kgriffs): Find a more general way to do this; we seem to be
# using this environ flag pattern over and over againg.
_TEST_INTEGRATION = os.environ.get('ZAQAR_TEST_INTEGRATION') is not None


class FunctionalTestBase(testing.TestBase):

    server = None
    server_class = None
    config_file = None
    class_bootstrap = None
    # NOTE(Eva-i): ttl_gc_interval is the known maximum time interval between
    # automatic resource TTL expirations. Depends on message store back end.
    class_ttl_gc_interval = None
    wipe_dbs_projects = set([])

    def setUp(self):
        super(FunctionalTestBase, self).setUp()
        # NOTE(flaper87): Config can't be a class
        # attribute because it may be necessary to
        # modify it at runtime which will affect
        # other instances running instances.
        self.cfg = config.load_config()

        if not self.cfg.run_tests:
            self.skipTest("Functional tests disabled")

        config_file = self.config_file or self.cfg.zaqar.config

        config_file = base_helpers.override_mongo_conf(config_file, self)

        self.mconf = self.load_conf(config_file)

        validator = validation.Validator(self.mconf)
        self.limits = validator._limits_conf

        transport_base._config_options()

        self.resource_defaults = transport_base.ResourceDefaults(self.mconf)

        # Always register options
        self.__class__.class_bootstrap = bootstrap.Bootstrap(self.mconf)
        self.class_bootstrap.transport

        datadriver = self.class_bootstrap.storage._storage
        if isinstance(datadriver, redis.DataDriver):
            self.__class__.class_ttl_gc_interval = 1
        if isinstance(datadriver, mongodb.DataDriver):
            # NOTE(kgriffs): MongoDB's TTL scavenger only runs once a minute
            self.__class__.class_ttl_gc_interval = 60

        if _TEST_INTEGRATION:
            if not (self.server and self.server.is_alive()):
                self.server = self.server_class()
                self.server.start(self.mconf)
                self.addCleanup(self.server.process.terminate)

            self.client = http.Client()
        else:
            if self.server_class == ZaqarAdminServer:
                self.mconf.pooling = True
                self.mconf.admin_mode = True

            self.addCleanup(self.class_bootstrap.storage.close)
            self.addCleanup(self.class_bootstrap.control.close)
            self.client = http.WSGIClient(self.class_bootstrap.transport.app)

        self.headers = helpers.create_zaqar_headers(self.cfg)

        self.headers_response_with_body = {'location', 'content-type'}

        self.client.set_headers(self.headers)

        # Store information required for cleaning databases after
        # execution of test class
        self.wipe_dbs_projects.add(self.headers["X-Project-ID"])

    def tearDown(self):
        super(FunctionalTestBase, self).tearDown()
        # Project might has changed during test case execution.
        # Lets add it again to the set.
        self.wipe_dbs_projects.add(self.headers["X-Project-ID"])

    @staticmethod
    def _if_mongo_datadriver_drop_dbs(driver):
        """Drops MongoDB datadriver's databases.

        :param driver: instance of zaqar.storage.mongodb.driver.DataDriver
        """
        if not isinstance(driver, mongodb.DataDriver):
            return
        for db in driver.message_databases:
            driver.connection.drop_database(db)
        subscription_db = driver.subscriptions_database
        driver.connection.drop_database(subscription_db)

    @staticmethod
    def _if_mongo_controldriver_drop_dbs(driver):
        """Drops all MongoDB controldriver's databases.

        :param driver: instance of zaqar.storage.mongodb.driver.ControlDriver
        """
        if not isinstance(driver, mongodb.ControlDriver):
            return
        driver.connection.drop_database(driver.database)
        driver.connection.drop_database(driver.queues_database)

    @classmethod
    def _pooling_drop_dbs_by_project(cls, xproject):
        """Finds all pool drivers by project, drops all their databases.

        Assumes that pooling is enabled.

        :param xproject: project name to use for pool drivers search
        """
        datadriver = cls.class_bootstrap.storage._storage
        controldriver = cls.class_bootstrap.control
        # Let's get list of all queues by project
        queue_generator = controldriver.queue_controller.list(project=xproject)
        queues = list(next(queue_generator))
        # Let's extract all queue names from the list of queues
        queue_names = [q['name'] for q in queues]
        # Finally let's use queues names to get each one of pool datadrivers
        catalog = datadriver._pool_catalog
        for queue_name in queue_names:
            pool_pipe_driver = catalog.lookup(queue_name, project=xproject)
            pool_datadriver = pool_pipe_driver._storage
            if pool_datadriver is not None:
                # Let's delete the queue, so the next invocation of
                # pooling_catalog.lookup() will not recreate pool driver
                controldriver.queue_controller.delete(queue_name)
                # Let's drop pool's databases
                cls._if_mongo_datadriver_drop_dbs(pool_datadriver)

    @classmethod
    def tearDownClass(cls):
        """Cleans up after test class execution.

        Drops all databases left.
        Closes connections to databases.
        """
        # Bootstrap can be None if all test cases were skipped, so nothing to
        # clean
        if cls.class_bootstrap is None:
            return

        datadriver = cls.class_bootstrap.storage._storage
        controldriver = cls.class_bootstrap.control

        if cls.class_bootstrap.conf.pooling:
            # Pooling detected, let's drop pooling-specific databases
            for p in cls.wipe_dbs_projects:
                # This will find all pool databases by project and drop them
                cls._pooling_drop_dbs_by_project(p)
            controldriver.pools_controller.drop_all()
            controldriver.flavors_controller.drop_all()
        else:
            # No pooling detected, let's just drop datadriver's databases
            cls._if_mongo_datadriver_drop_dbs(datadriver)

        cls.class_bootstrap.storage.close()

        # Let's drop controldriver's databases
        controldriver.catalogue_controller.drop_all()
        cls._if_mongo_controldriver_drop_dbs(controldriver)

        controldriver.close()

    def assertIsSubset(self, required_values, actual_values):
        """Checks if a list is subset of another.

        :param required_values: superset list.
        :param required_values: subset list.
        """

        form = 'Missing Header(s) - {0}'
        self.assertTrue(required_values.issubset(actual_values),
                        msg=form.format((required_values - actual_values)))

    def assertMessageCount(self, actualCount, expectedCount):
        """Checks if number of messages returned <= limit

        :param expectedCount: limit value passed in the url (OR) default(10).
        :param actualCount: number of messages returned in the API response.
        """
        msg = ('More Messages returned than allowed: expected count = {0}'
               ', actual count = {1}'.format(expectedCount, actualCount))
        self.assertLessEqual(actualCount, expectedCount, msg)

    def assertQueueStats(self, result_json, claimed):
        """Checks the Queue Stats results

        :param result_json: json response returned for Queue Stats.
        :param claimed: expected number of claimed messages.
        """
        total = self.limits.max_messages_per_claim_or_pop
        free = total - claimed

        self.assertEqual(claimed, result_json['messages']['claimed'])
        self.assertEqual(free, result_json['messages']['free'])
        self.assertEqual(total, result_json['messages']['total'])

        if 'oldest' in result_json['messages']:
            oldest_message = result_json['messages']['oldest']
            self.verify_message_stats(oldest_message)

            newest_message = result_json['messages']['newest']
            self.verify_message_stats(newest_message)

    def assertSchema(self, response, expectedSchemaName):
        """Compares the json response with the expected schema

        :param response: response json returned by the API.
        :type response: dict
        :param expectedSchema: expected schema definition for response.
        :type expectedSchema: string
        """
        try:
            expectedSchema = self.response.get_schema(expectedSchemaName)
            jsonschema.validate(response, expectedSchema)
        except jsonschema.ValidationError as message:
            assert False, message

    def verify_message_stats(self, message):
        """Verifies the oldest & newest message stats

        :param message: oldest (or) newest message returned by
                        queue_name/stats.
        """
        expected_keys = ['age', 'created', 'href']

        response_keys = message.keys()
        response_keys = sorted(response_keys)
        self.assertEqual(expected_keys, response_keys)

        # Verify that age has valid values
        age = message['age']
        msg = 'Invalid Age {0}'.format(age)
        self.assertLessEqual(0, age, msg)
        self.assertLessEqual(age, self.limits.max_message_ttl, msg)

        # Verify that GET on href returns 200
        path = message['href']
        result = self.client.get(path)
        self.assertEqual(200, result.status_code)

        # Verify that created time falls within the last 10 minutes
        # NOTE(malini): The messages are created during the test.
        created_time = message['created']
        created_time = timeutils.normalize_time(
            timeutils.parse_isotime(created_time))
        now = timeutils.utcnow()

        delta = timeutils.delta_seconds(before=created_time, after=now)
        # NOTE(malini): The 'int()' below is a work around  for the small time
        # difference between julianday & UTC.
        # (needed to pass this test on sqlite driver)
        delta = int(delta)

        msg = ('Invalid Time Delta {0}, Created time {1}, Now {2}'
               .format(delta, created_time, now))
        self.assertLessEqual(0, delta, msg)
        self.assertLessEqual(delta, 6000, msg)


@six.add_metaclass(abc.ABCMeta)
class Server(object):

    name = "zaqar-functional-test-server"

    def __init__(self):
        self.process = None

    @abc.abstractmethod
    def get_target(self, conf):
        """Prepares the target object

        This method is meant to initialize server's
        bootstrap and return a callable to run the
        server.

        :param conf: The config instance for the
            bootstrap class
        :returns: A callable object
        """

    def is_alive(self):
        """Returns True IFF the server is running."""

        if self.process is None:
            return False

        return self.process.is_alive()

    def start(self, conf):
        """Starts the server process.

        :param conf: The config instance to use for
            the new process
        :returns: A `multiprocessing.Process` instance
        """

        # TODO(flaper87): Re-use running instances.
        target = self.get_target(conf)

        if not callable(target):
            raise RuntimeError("Target not callable")

        self.process = multiprocessing.Process(target=target,
                                               name=self.name)
        self.process.daemon = True
        self.process.start()

        # NOTE(flaper87): Give it a second
        # to boot.
        self.process.join(1)
        return self.process

    def stop(self):
        """Terminates a process

        This method kills a process by
        calling `terminate`. Note that
        children of this process won't be
        terminated but become orphaned.
        """
        self.process.terminate()


class ZaqarServer(Server):

    name = "zaqar-wsgiref-test-server"

    def get_target(self, conf):
        server = bootstrap.Bootstrap(conf)
        return server.run


class ZaqarAdminServer(Server):

    name = "zaqar-admin-wsgiref-test-server"

    def get_target(self, conf):
        conf.admin_mode = True
        server = bootstrap.Bootstrap(conf)
        return server.run


class V1FunctionalTestBase(FunctionalTestBase):
    def setUp(self):
        super(V1FunctionalTestBase, self).setUp()
        self.response = response_v1.ResponseSchema(self.limits)


class V1_1FunctionalTestBase(FunctionalTestBase):
    def setUp(self):
        super(V1_1FunctionalTestBase, self).setUp()
        self.response = response_v1_1.ResponseSchema(self.limits)


class V2FunctionalTestBase(FunctionalTestBase):
    def setUp(self):
        super(V2FunctionalTestBase, self).setUp()
        self.response = response_v2.ResponseSchema(self.limits)

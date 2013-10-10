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


from marconi.openstack.common import timeutils
from marconi.queues import bootstrap
# NOTE(flaper87): This is necessary to register,
# wsgi configs and won't be permanent. It'll be
# refactored as part of the work for this blueprint
from marconi.queues.transport import validation
from marconi.queues.transport import wsgi  # noqa
from marconi import tests as testing
from marconi.tests.functional import config
from marconi.tests.functional import helpers
from marconi.tests.functional import http


class FunctionalTestBase(testing.TestBase):

    server = None
    server_class = None

    def setUp(self):
        super(FunctionalTestBase, self).setUp()

        # NOTE(flaper87): Config can't be a class
        # attribute because it may be necessary to
        # modify it at runtime which will affect
        # other instances running instances.
        self.cfg = config.load_config()

        if not self.cfg.run_tests:
            self.skipTest("Functional tests disabled")

        self.mconf = self.load_conf(self.cfg.marconi.config)

        # NOTE(flaper87): Use running instances.
        if (self.cfg.marconi.run_server and not
                self.server):
            self.server = self.server_class()
            self.server.start(self.mconf)

        validator = validation.Validator(self.mconf)
        self.limits = validator._limits_conf

        # NOTE(flaper87): Create client
        # for this test unit.
        self.client = http.Client()
        self.headers = helpers.create_marconi_headers(self.cfg)

        if self.cfg.auth.auth_on:
            auth_token = helpers.get_keystone_token(self.cfg, self.client)
            self.headers["X-Auth-Token"] = auth_token

        self.headers_response_with_body = set(['location',
                                               'content-type'])

        self.client.set_headers(self.headers)

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.process.terminate()

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
        msg = 'More Messages returned than allowed: expected count = {0}' \
              ', actual count = {1}'.format(expectedCount, actualCount)
        self.assertTrue(actualCount <= expectedCount, msg)

    def assertQueueStats(self, result_json, claimed):
        """Checks the Queue Stats results

        :param result_json: json response returned for Queue Stats.
        :param claimed: expected number of claimed messages.
        """
        total = self.limits.message_paging_uplimit
        free = total - claimed

        self.assertEqual(result_json['messages']['claimed'], claimed)
        self.assertEqual(result_json['messages']['free'],
                         free)
        self.assertEqual(result_json['messages']['total'],
                         total)

        if 'oldest' in result_json['messages']:
            oldest_message = result_json['messages']['oldest']
            self.verify_message_stats(oldest_message)

            newest_message = result_json['messages']['newest']
            self.verify_message_stats(newest_message)

    def verify_message_stats(self, message):
        """Verifies the oldest & newest message stats

        :param message: oldest (or) newest message returned by
                        queue_name/stats.
        """
        expected_keys = ['age', 'created', 'href']

        response_keys = message.keys()
        response_keys.sort()
        self.assertEqual(response_keys, expected_keys)

        # Verify that age has valid values
        age = message['age']
        self.assertTrue(0 <= age <= self.limits.message_ttl_max,
                        msg='Invalid Age {0}'.format(age))

        # Verify that GET on href returns 200
        path = message['href']
        result = self.client.get(path)
        self.assertEqual(result.status_code, 200)

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

        msg = 'Invalid Time Delta {0}, Created time {1}, Now {2}' \
              .format(delta, created_time, now)
        self.assertTrue(0 <= delta <= 6000, msg)


class Server(object):

    __metaclass__ = abc.ABCMeta

    servers = {}
    name = "marconi-functional-test-server"

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


class MarconiServer(Server):

    name = "marconi-wsgiref-test-server"

    def get_target(self, conf):
        server = bootstrap.Bootstrap(conf)
        return server.run


class MarconiAdminServer(Server):

    name = "marconi-admin-wsgiref-test-server"

    def get_target(self, conf):
        conf.admin_mode = True
        server = bootstrap.Bootstrap(conf)
        conf.admin_mode = False
        return server.run

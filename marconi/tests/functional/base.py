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

from marconi.queues import bootstrap
# NOTE(flaper87): This is necessary to register,
# wsgi configs and won't be permanent. It'll be
# refactored as part of the work for this blueprint
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

        # NOTE(flaper87): Use running instances.
        if (self.cfg.marconi.run_server and not
                self.server):
            self.server = self.server_class()
            self.server.start(self.conf_path(self.cfg.marconi.config))

        self.mconf = self.load_conf(self.cfg.marconi.config).conf
        self.limits = self.mconf['queues:limits:transport']

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

    def assertMessageCount(self, expectedCount, actualCount):
        """Checks if number of messages returned <= limit

        :param expectedCount: limit value passed in the url (OR) default(10).
        :param actualCount: number of messages returned in the API response.
        """
        self.assertTrue(actualCount <= expectedCount,
                        msg='More Messages returned than allowed')


class Server(object):

    __metaclass__ = abc.ABCMeta

    servers = {}
    name = "marconi-functional-test-server"

    def __init__(self):
        self.process = None

    @abc.abstractmethod
    def get_target(self, config_file):
        """Prepares the target object

        This method is meant to initialize server's
        bootstrap and return a callable to run the
        server.

        :param config_file: The configuration file
                            for the bootstrap class
        :returns: A callable object.
        """

    def start(self, config_file):
        """Starts the server process.

        :param config_file: The configuration file
                            to use for the new process
        :returns: A `multiprocessing.Process` instance
        """

        # TODO(flaper87): Re-use running instances.
        target = self.get_target(config_file)

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

    def get_target(self, config_file):
        server = bootstrap.Bootstrap(config_file)
        return server.run

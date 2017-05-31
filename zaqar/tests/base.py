# Copyright (c) 2013 Rackspace Hosting, Inc.
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

import os

import fixtures
from oslo_config import cfg
from oslo_log import log
from osprofiler import opts
import testtools

from zaqar.common import configs
from zaqar.tests import helpers


class TestBase(testtools.TestCase):
    """Child class of testtools.TestCase for testing Zaqar.

    Inherit from this and write your test methods. If the child class defines
    a prepare(self) method, this method will be called before executing each
    test method.
    """

    config_file = None

    def setUp(self):
        super(TestBase, self).setUp()

        self.useFixture(fixtures.FakeLogger('zaqar'))

        if os.environ.get('OS_STDOUT_CAPTURE') is not None:
            stdout = self.useFixture(fixtures.StringStream('stdout')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stdout', stdout))
        if os.environ.get('OS_STDERR_CAPTURE') is not None:
            stderr = self.useFixture(fixtures.StringStream('stderr')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stderr', stderr))

        if self.config_file:
            self.config_file = helpers.override_mongo_conf(
                self.config_file, self)
            self.conf = self.load_conf(self.config_file)
        else:
            self.conf = cfg.ConfigOpts()

        self.conf.register_opts(configs._GENERAL_OPTIONS)
        self.conf.register_opts(configs._DRIVER_OPTIONS,
                                group=configs._DRIVER_GROUP)
        self.conf.register_opts(configs._NOTIFICATION_OPTIONS,
                                group=configs._NOTIFICATION_GROUP)
        self.conf.register_opts(configs._NOTIFICATION_OPTIONS,
                                group=configs._NOTIFICATION_GROUP)
        self.conf.register_opts(configs._SIGNED_URL_OPTIONS,
                                group=configs._SIGNED_URL_GROUP)
        opts.set_defaults(self.conf)
        self.conf.register_opts(configs._PROFILER_OPTIONS,
                                group=configs._PROFILER_GROUP)

        self.mongodb_url = os.environ.get('ZAQAR_TEST_MONGODB_URL',
                                          'mongodb://127.0.0.1:27017')

    @classmethod
    def conf_path(cls, filename):
        """Returns the full path to the specified Zaqar conf file.

        :param filename: Name of the conf file to find (e.g.,
                         'wsgi_memory.conf')
        """

        if os.path.exists(filename):
            return filename

        return os.path.join(os.environ["ZAQAR_TESTS_CONFIGS_DIR"], filename)

    @classmethod
    def load_conf(cls, filename):
        """Loads `filename` configuration file.

        :param filename: Name of the conf file to find (e.g.,
                         'wsgi_memory.conf')

        :returns: Project's config object.
        """
        conf = cfg.ConfigOpts()
        log.register_options(conf)
        conf(args=[], default_config_files=[cls.conf_path(filename)])
        return conf

    def config(self, group=None, **kw):
        """Override some configuration values.

        The keyword arguments are the names of configuration options to
        override and their values.

        If a group argument is supplied, the overrides are applied to
        the specified configuration option group.

        All overrides are automatically cleared at the end of the current
        test by the tearDown() method.
        """
        for k, v in kw.items():
            self.conf.set_override(k, v, group)

    def _my_dir(self):
        return os.path.abspath(os.path.dirname(__file__))

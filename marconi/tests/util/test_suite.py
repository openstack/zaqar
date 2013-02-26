"""Defines the TestSuite class.

Copyright 2013 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import testtools
import os.path


class TestSuite(testtools.TestCase):
    """Child class of testtools.TestCase for testing Marconi

    Inherit from this and write your test methods. If the child class defines
    a prepare(self) method, this method will be called before executing each
    test method.

    Attributes:
        api: falcon.API instance used in simulating requests.
        srmock: falcon.testing.StartResponseMock instance used in
            simulating requests.
        test_route: Randomly-generated route string (path) that tests can
            use when wiring up resources.


    """

    def setUp(self):
        """Initializer, unittest-style"""

        super(TestSuite, self).setUp()

        prepare = getattr(self, 'prepare', None)
        if hasattr(prepare, '__call__'):
            prepare()

    def conf_path(self, filename):
        """ Returns the full path to the specified Marconi conf file

        Args:
            filename: Name of the conf file to find (e.g., "wsgi_memory.conf")

        """

        parent = os.path.dirname(self._my_dir())
        return os.path.join(parent, 'etc', filename)

    def _my_dir(self):
        return os.path.abspath(os.path.dirname(__file__))

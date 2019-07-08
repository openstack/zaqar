..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=============
Running tests
=============

Zaqar contains a suite of tests (both unit and functional) in the
``zaqar/tests`` directory.

 See :doc:`test_suite` for details.

Any proposed code change is automatically rejected by the OpenStack Jenkins
server [#f1]_ if the change causes test failures.

It is recommended for developers to run the test suite before submitting patch
for review. This allows to catch errors as early as possible.

Preferred way to run the tests
------------------------------

The preferred way to run the unit tests is using ``tox``. It executes tests in
isolated environment, by creating separate virtualenv and installing
dependencies from the ``requirements.txt`` and ``test-requirements.txt`` files,
so the only package you install is ``tox`` itself:

.. code-block:: console

    $ pip install tox

See `the unit testing section of the Testing wiki page`_ for more information.
Following are some simple examples.

To run the Python 2.7 tests:

.. code-block:: console

    $ tox -e py27

To run the style tests:

.. code-block:: console

    $ tox -e pep8

To run multiple tests separate items by commas:

.. code-block:: console

    $ tox -e py27,py35,pep8

.. _the unit testing section of the Testing wiki page: https://wiki.openstack.org/wiki/Testing#Unit_Tests

Running a subset of tests
^^^^^^^^^^^^^^^^^^^^^^^^^

Instead of running all tests, you can specify an individual directory, file,
class or method that contains test code, i.e. filter full names of tests by a
string.

To run the tests located only in the ``zaqar/tests/unit/storage``
directory use:

.. code-block:: console

    $ tox -e py27 -- zaqar.tests.unit.storage

To run the tests specific to the MongoDB driver in the
``zaqar/tests/unit/storage/test_impl_mongodb.py`` file:

.. code-block:: console

    $ tox -e py27 -- test_impl_mongodb

To run the tests in the ``MongodbMessageTests`` class in
the ``tests/unit/storage/test_impl_mongodb.py`` file:

.. code-block:: console

    $ tox -e py27 -- test_impl_mongodb.MongodbMessageTests

To run the ``MongodbMessageTests.test_message_lifecycle`` test method in
the ``tests/unit/storage/test_impl_mongodb.py`` file:

.. code-block:: console

    $ tox -e py27 -- test_impl_mongodb.MongodbMessageTests.test_message_lifecycle

Running functional tests
------------------------

Zaqar's functional tests treat Zaqar as a black box. In other words, the API
calls attempt to simulate an actual user. Unlike unit tests, the functional
tests do not use mockendpoints.

Functional test modes
^^^^^^^^^^^^^^^^^^^^^

Functional tests can run in integration mode and non-integration mode.

Integration mode
""""""""""""""""

In integration mode functional tests are performed on Zaqar server instances
running as separate processes. This is real functional testing.

To run functional tests in integration mode, execute:

.. code-block:: console

    $ tox -e integration

Non-integration mode
""""""""""""""""""""

In non-integration mode functional tests are performed on Zaqar server
instances running as python objects. This mode doesn't guarantee enough black
boxness for Zaqar, but tests run 10 times faster than in integration mode.

To run functional tests in non-integration mode, execute:

.. code-block:: console

    $ tox -e py27 -- zaqar.tests.functional

Using a custom MongoDB instance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you need to run functional tests against a non-default MongoDB installation,
you can set the ``ZAQAR_TEST_MONGODB_URL`` and ``ZAQAR_TEST_MONGODB``
environment variables. For example:

.. code-block:: console

    $ export ZAQAR_TEST_MONGODB=True
    $ export ZAQAR_TEST_MONGODB_URL=mongodb://remote-server:27017

Using custom parameters
^^^^^^^^^^^^^^^^^^^^^^^

You can edit default functional test configuration file
``zaqar/tests/etc/functional-tests.conf`` according to your needs.

For example, you want to run functional tests with keystone authentication
enabled, input a valid set of credentials to ``[auth]`` section in
configuration file and set ``auth_on`` parameter to ``True``.

Using local Mysql database
^^^^^^^^^^^^^^^^^^^^^^^^^^

To use a similar testing environment with database support like upstream CI,
you can run ``zaqar/tools/test-setup.sh`` to create a required Mysql user
``openstack_citest`` with same password. The user is required by oslo.db's
test. Zaqar needs it because Zaqar's sqlalchemy database migration is
leveraging oslo.db's migration test base.

.. rubric:: Footnotes

.. [#f1] See https://docs.openstack.org/infra/system-config/jjb.html

Running tests
=============

Zaqar contains a suite of tests (both unit and functional) in the
``zaqar/tests`` and ``tests`` directories.

Any proposed code change is automatically rejected by the OpenStack Jenkins
server [#f1]_ if the change causes test failures.

It is recommended for developers to run the test suite before submitting patch
for review. This allows to catch errors as early as possible.

Preferred way to run the tests
------------------------------

The preferred way to run the unit tests is using ``tox``.  It executes tests in
isolated environment, by creating separate virtualenv and installing
dependencies from the ``requirements.txt`` and ``test-requirements.txt`` files,
so the only package you install is ``tox`` itself::

    pip install tox

See `the unit testing section of the Testing wiki page`_ for more information.
Following are some simple examples.

To run the Python 2.6 tests::

    tox -e py26

To run the style tests::

    tox -e pep8

To run multiple tests separate items by commas::

    tox -e py27,pep8

.. _the unit testing section of the Testing wiki page: https://wiki.openstack.org/wiki/Testing#Unit_Tests

Running a subset of tests
-------------------------

Instead of running all tests, you can specify an individual directory, file,
class, or method that contains test code.

To run the tests located only in the ``tests/unit/queues/storage`` directory use::

    tox -e py27 tests.unit.queues.storage

To run the tests specific to the MongoDB driver in the ``tests/unit/queues/storage/test_impl_mongodb.py`` file::

    tox -e py27 test_impl_mongodb

To run the tests in the ``MongodbMessageTests`` class in
the ``tests/unit/queues/storage/test_impl_mongodb.py`` file::

    tox -e py27 test_impl_mongodb.MongodbMessageTests

To run the `MongodbMessageTests.test_message_lifecycle` test method in
the ``tests/unit/queues/storage/test_impl_mongodb.py`` file::

    tox -e py27 test_impl_mongodb.MongodbMessageTests.test_message_lifecycle

.. rubric:: Footnotes

.. [#f1] See http://ci.openstack.org/jenkins.html

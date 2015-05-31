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

import contextlib
import functools
import os
import tempfile
import uuid

import six
import testtools


RUN_ALL_TESTS = os.environ.get('ZAQAR_TEST_EVERYTHING')


def _test_variable_set(variable):
    return os.environ.get(variable, RUN_ALL_TESTS) is None


SKIP_SLOW_TESTS = _test_variable_set('ZAQAR_TEST_SLOW')
SKIP_MONGODB_TESTS = _test_variable_set('ZAQAR_TEST_MONGODB')
SKIP_REDIS_TESTS = _test_variable_set('ZAQAR_TEST_REDIS')
SKIP_SWIFT_TESTS = _test_variable_set('ZAQAR_TEST_SWIFT')


@contextlib.contextmanager
def expect(*exc_type):
    """A context manager to validate raised exceptions.

    Can be used as an alternative to testtools.ExpectedException.

    Notable differences:
        1. This context manager accepts child classes of the
           given type, testing that an "except" statement
           referencing the given type would indeed catch it when
           raised by the statement(s) defined inside the context.
        2. When the expected exception (or a child thereof) is
           not raised, this context manager *always* raises
           an AssertionError, both when a different exception
           is raised, and when no exception is raised at all.

    :param *exc_type: Exception type(s) expected to be raised during
        execution of the "with" context.
    """
    assert len(exc_type) > 0

    try:
        yield
    except exc_type:
        pass
    else:
        raise AssertionError(
            'Not raised: %s' % ', '.join(e.__name__ for e in exc_type))


@contextlib.contextmanager
def partitions(controller, count):
    """Context manager to create several partitions for testing.

    The partitions are automatically deleted when the context manager
    goes out of scope.

    :param controller:
    :param count: int - number of partitions to create
    :returns: [(str, int, [str])] - names, weights, hosts
    """
    spec = [(six.text_type(uuid.uuid1()), i,
             [six.text_type(i)]) for i in range(count)]
    for n, w, h in spec:
        controller.create(n, w, h)

    yield spec

    for n, _, _ in spec:
        controller.delete(n)


@contextlib.contextmanager
def partition(controller, name, weight, hosts):
    """Context manager to create a single partition for testing.

    The partition is automatically deleted when the context manager
    goes out of scope.

    :param controller: storage handler
    :param name: str - partition name
    :param weight: int - partition weight
    :param hosts: [str] - hosts associated with this partition
    :returns: (str, int, [str]) - name, weight, host used in construction
    """
    controller.create(name, weight, hosts)
    yield (name, weight, hosts)
    controller.delete(name)


@contextlib.contextmanager
def entry(controller, project, queue, partition, host, metadata={}):
    """Context manager to create a catalogue entry for testing.

    The entry is automatically deleted when the context manager
    goes out of scope.

    :param controller: storage handler
    :param project: str - namespace for queue
    :param queue: str - name of queue
    :param partition: str - associated partition
    :param host: str - representative host
    :param metadata: dict - metadata representation for this entry
    :returns: (str, str, str, str, dict) - (project, queue, part, host, meta)
    """
    controller.insert(project, queue, partition, host, metadata)
    yield (project, queue, partition, host, metadata)
    controller.delete(project, queue)


@contextlib.contextmanager
def entries(controller, count):
    """Context manager to create several catalogue entries for testing.

    The entries are automatically deleted when the context manager
    goes out of scope.

    :param controller: storage handler
    :param count: int - number of entries to create
    :returns: [(str, str, str, str)] - [(project, queue, partition, host)]
    """
    spec = [(u'_', six.text_type(uuid.uuid1()), six.text_type(i),
             six.text_type(i))
            for i in range(count)]

    for p, q, n, h in spec:
        controller.insert(p, q, n, h)

    yield spec

    for p, q, _, _ in spec:
        controller.delete(p, q)


@contextlib.contextmanager
def pool_entry(controller, project, queue, pool):
    """Context manager to create a catalogue entry for testing.

    The entry is automatically deleted when the context manager
    goes out of scope.

    :param controller: storage handler
    :type controller: queues.storage.base:CatalogueBase
    :param project: namespace for queue
    :type project: six.text_type
    :param queue: name of queue
    :type queue: six.text_type
    :param pool: an identifier for the pool
    :type pool: six.text_type
    :returns: (project, queue, pool)
    :rtype: (six.text_type, six.text_type, six.text_type)
    """
    controller.insert(project, queue, pool)
    yield (project, queue, pool)
    controller.delete(project, queue)


@contextlib.contextmanager
def pool_entries(controller, pool_ctrl, count):
    """Context manager to create several catalogue entries for testing.

    The entries are automatically deleted when the context manager
    goes out of scope.

    :param controller: storage handler
    :type controller: queues.storage.base:CatalogueBase
    :param count: number of entries to create
    :type count: int
    :returns: [(project, queue, pool)]
    :rtype: [(six.text_type, six.text_type, six.text_type)]
    """
    spec = [(u'_', six.text_type(uuid.uuid1()), six.text_type(i))
            for i in range(count)]

    for p, q, s in spec:
        pool_ctrl.create(s, 100, s)
        controller.insert(p, q, s)

    yield spec

    for p, q, s in spec:
        controller.delete(p, q)
        pool_ctrl.delete(s)


def requires_mongodb(test_case):
    """Decorator to flag a test case as being dependent on MongoDB.

    MongoDB-specific tests will be skipped unless the ZAQAR_TEST_MONGODB
    environment variable is set. If the variable is set, the tests will
    assume that mongod is running and listening on localhost.
    """

    reason = ('Skipping tests that require MongoDB. Ensure '
              'mongod is running on localhost and then set '
              'ZAQAR_TEST_MONGODB in order to enable tests '
              'that are specific to this storage backend. ')

    return testtools.skipIf(SKIP_MONGODB_TESTS, reason)(test_case)


def requires_redis(test_case):
    """Decorator to flag a test case as being dependent on Redis.

    Redis-specific tests will be skipped unless the ZAQAR_TEST_REDIS
    environment variable is set. If the variable is set, the tests will
    assume that redis is running and listening on localhost.
    """

    reason = ('Skipping tests that require Redis. Ensure '
              'Redis is running on localhost and then set '
              'ZAQAR_TEST_REDIS in order to enable tests '
              'that are specific to this storage backend. ')

    return testtools.skipIf(SKIP_REDIS_TESTS, reason)(test_case)


def requires_swift(test_case):
    """Decorator to flag a test case as being dependent on Swift.

    Redis-specific tests will be skipped unless the ZAQAR_TEST_SWIFT
    environment variable is set. If the variable is set, the tests will
    assume that Swift is accessible and configured properly.
    """

    reason = ('Skipping tests that require Swift. Ensure Swift is running '
              'and then set ZAQAR_TEST_SWIFT in order to enable tests '
              'that are specific to this storage backend. ')

    return testtools.skipIf(SKIP_SWIFT_TESTS, reason)(test_case)


def is_slow(condition=lambda self: True):
    """Decorator to flag slow tests.

    Slow tests will be skipped unless ZAQAR_TEST_SLOW is set, and
    condition(self) returns True.

    :param condition: Function that returns True IFF the test will be slow;
        useful for child classes which may modify the behavior of a test
        such that it may or may not be slow.
    """

    def decorator(test_method):
        @functools.wraps(test_method)
        def wrapper(self):
            if SKIP_SLOW_TESTS and condition(self):
                msg = ('Skipping slow test. Set ZAQAR_TEST_SLOW '
                       'to enable slow tests.')

                self.skipTest(msg)

            test_method(self)

        return wrapper

    return decorator


def override_mongo_conf(conf_file, test):
    test_mongo_url = os.environ.get('ZAQAR_TEST_MONGODB_URL')
    if test_mongo_url:
        parser = six.moves.configparser.ConfigParser()
        parser.read(test.conf_path(conf_file))
        sections = ['drivers:management_store:mongodb',
                    'drivers:message_store:mongodb']
        for section in sections:
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, 'uri', test_mongo_url)
        if not parser.has_section('oslo_policy'):
            parser.add_section('oslo_policy')
        parser.set('oslo_policy', 'policy_file', test.conf_path('policy.json'))
        fd, path = tempfile.mkstemp()
        conf_fd = os.fdopen(fd, 'w')
        try:
            parser.write(conf_fd)
        finally:
            conf_fd.close()
        test.addCleanup(os.remove, path)
        return path
    else:
        return conf_file

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
import uuid

import six

SKIP_SLOW_TESTS = os.environ.get('MARCONI_TEST_SLOW') is None


@contextlib.contextmanager
def expect(*exc_type):
    """A context manager to validate raised expections.

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
    """context_manager: Creates `count` partitions in storage,
    and deletes them once this goes out of scope.

    :param partitions_controller:
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
    """context_manager: Creates a single partition that is deleted
    once this context manager goes out of scope.

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
    """Creates a catalogue entry with the given details, and deletes
    it once the context manager goes out of scope.

    :param controller: storage handler
    :param project: str - namespace for queue
    :param queue: str - name of queue
    :param partition: str - associated partition
    :param host: str - representative host
    :returns: (str, str, str, str, dict) - (project, queue, part, host, meta)
    """
    controller.insert(project, queue, partition, host, metadata)
    yield (project, queue, partition, host, metadata)
    controller.delete(project, queue)


@contextlib.contextmanager
def entries(controller, count):
    """Creates `count` catalogue entries with the given details, and
    deletes them once the context manager goes out of scope.

    :param controller: storage handler
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


def is_slow(condition=lambda self: True):
    """Decorator to flag slow tests.

    Slow tests will be skipped if MARCONI_TEST_SLOW is set, and
    condition(self) returns True.

    :param condition: Function that returns True IFF the test will be slow;
        useful for child classes which may modify the behavior of a test
        such that it may or may not be slow.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self):
            if SKIP_SLOW_TESTS and condition(self):
                msg = ('Skipping slow test. Set MARCONI_TEST_SLOW '
                       'to enable slow tests.')

                self.skipTest(msg)

            func(self)

        return wrapper

    return decorator

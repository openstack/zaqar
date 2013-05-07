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

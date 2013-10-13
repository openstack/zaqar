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

from marconi.common import pipeline
from marconi.tests import base


class FirstClass(object):

    def with_args(self, name):
        return name

    def with_kwargs(self, lastname='yo'):
        return lastname

    def with_args_kwargs(self, name, lastname='yo'):
        return '{0} {1}'.format(name, lastname)

    def no_args(self):
        return True

    def does_nothing(self):
        return None

    def calls_the_latest(self):
        return None


class SecondClass(object):

    def does_nothing(self):
        return None

    def calls_the_latest(self):
        return True

    def _raise_rterror(self):
        raise RuntimeError("It shouldn't get here!")

    # NOTE(flaper87): This methods will be used to test
    # that the pipeline stops at the first class returning
    # something.
    with_args = with_kwargs = no_args = _raise_rterror


class TestPipeLine(base.TestBase):

    def setUp(self):
        super(TestPipeLine, self).setUp()
        self.pipeline = pipeline.Pipeline([FirstClass(),
                                           SecondClass()])

    def test_attribute_error(self):
        consumer = self.pipeline.consumer_for('does_not_exist')
        self.assertRaises(AttributeError, consumer)

    def test_with_args(self):
        name = 'James'
        self.assertEqual(self.pipeline.with_args(name), name)

    def test_with_kwargs(self):
        lastname = 'Bond'
        self.assertEqual(self.pipeline.with_kwargs(lastname), lastname)
        self.assertEqual(self.pipeline.with_kwargs(lastname=lastname),
                         lastname)

    def test_with_args_kwargs(self):
        fullname = 'James Bond'
        name, lastname = fullname.split()
        result = self.pipeline.with_args_kwargs(name, lastname=lastname)
        self.assertEqual(result, fullname)

    def test_does_nothing(self):
        self.assertIsNone(self.pipeline.does_nothing())

    def test_calls_the_latest(self):
        self.assertTrue(self.pipeline.calls_the_latest())

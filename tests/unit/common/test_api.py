# Copyright (c) 2013 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from zaqar.common.api import api
from zaqar.common import errors
from zaqar.tests import base


class FakeApi(api.Api):
    schema = {
        'test_operation': {
            'ref': 'test/{name}',
            'method': 'GET',
            'properties': {
                'name': {'type': 'string'},
                'address': {'type': 'string'}
            },

            'additionalProperties': False,
            'required': ['name']
        }
    }


class TestApi(base.TestBase):

    def setUp(self):
        super(TestApi, self).setUp()
        self.api = FakeApi()

    def test_valid_params(self):
        self.assertTrue(self.api.validate('test_operation',
                                          {'name': 'Sauron'}))

    def test_invalid_params(self):
        self.assertFalse(self.api.validate('test_operation',
                                           {'name': 'Sauron',
                                            'lastname': 'From Mordor'}))

    def test_missing_params(self):
        self.assertFalse(self.api.validate('test_operation', {}))

    def test_invalid_operation(self):
        self.assertRaises(errors.InvalidAction, self.api.validate,
                          'super_secret_op', {})

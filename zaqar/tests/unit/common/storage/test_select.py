# Copyright (c) 2013 Rackspace, Inc.
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

import testtools

from zaqar.common.storage import select


class TestSelect(testtools.TestCase):

    def test_weighted_returns_none_if_no_objs(self):
        self.assertIsNone(select.weighted([]))

    def test_weighted_returns_none_if_objs_have_zero_weight(self):
        objs = [{'weight': 0, 'name': str(i)} for i in range(2)]
        self.assertIsNone(select.weighted(objs))

    def test_weighted_ignores_zero_weight_objs(self):
        objs = [{'weight': 0, 'name': str(i)} for i in range(2)]
        expect = {'weight': 1, 'name': 'theone'}
        objs.append(expect)
        self.assertEqual(expect, select.weighted(objs))

    def test_weighted_returns_an_object_it_was_given(self):
        objs = [{'weight': 10, 'name': str(i)} for i in range(10)]
        ret = select.weighted(objs)
        self.assertIn(ret, objs)

    def test_weighted_returns_none_if_selector_oob(self):
        objs = [{'weight': 10, 'name': str(i)} for i in range(10)]
        sum_weights = sum([o['weight'] for o in objs])
        capped_gen = lambda x, y: sum_weights
        self.assertIsNone(select.weighted(objs,
                                          generator=capped_gen))

    def test_weighted_returns_first_if_selector_is_zero(self):
        objs = [{'weight': 10, 'name': str(i)} for i in range(10)]
        zero_gen = lambda x, y: 0
        self.assertEqual(objs[0],
                         select.weighted(objs, generator=zero_gen))

    def test_weighted_returns_last_if_selector_is_sum_minus_one(self):
        objs = [{'weight': 10, 'name': str(i)} for i in range(10)]
        sum_weights = sum([o['weight'] for o in objs])
        capped_gen = lambda x, y: sum_weights - 1
        self.assertEqual(objs[-1],
                         select.weighted(objs, generator=capped_gen))

    def test_weighted_boundaries(self):
        objs = [{'weight': 1, 'name': str(i)} for i in range(3)]
        for i in range(len(objs)):
            fixed_gen = lambda x, y: i
            self.assertEqual(objs[i],
                             select.weighted(objs, generator=fixed_gen))

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


from marconi.common import decorators
from marconi.tests import util as testing


class TestLazyProperty(testing.TestBase):

    class DecoratedClass(object):

        @decorators.lazy_property(write=True)
        def read_write_delete(self):
            return True

        @decorators.lazy_property(write=True, delete=False)
        def read_write(self):
            return True

        @decorators.lazy_property()
        def read_delete(self):
            return True

    def setUp(self):
        super(TestLazyProperty, self).setUp()
        self.cls_instance = self.DecoratedClass()

    def test_write_delete(self):
        self.assertTrue(self.cls_instance.read_write_delete)
        self.assertTrue(hasattr(self.cls_instance, "_lazy_read_write_delete"))

        self.cls_instance.read_write_delete = False
        self.assertFalse(self.cls_instance.read_write_delete)

        del self.cls_instance.read_write_delete
        self.assertFalse(hasattr(self.cls_instance, "_lazy_read_write_delete"))

    def test_write(self):
        self.assertTrue(self.cls_instance.read_write)
        self.assertTrue(hasattr(self.cls_instance, "_lazy_read_write"))

        self.cls_instance.read_write = False
        self.assertFalse(self.cls_instance.read_write)

        try:
            del self.cls_instance.read_write
            self.fail()
        except TypeError:
            # Bool object is not callable
            self.assertTrue(hasattr(self.cls_instance, "_lazy_read_write"))

    def test_delete(self):
        self.assertTrue(self.cls_instance.read_delete)
        self.assertTrue(hasattr(self.cls_instance, "_lazy_read_delete"))

        try:
            self.cls_instance.read_delete = False
            self.fail()
        except TypeError:
            # Bool object is not callable
            pass

        del self.cls_instance.read_delete
        self.assertFalse(hasattr(self.cls_instance, "_lazy_read_delete"))

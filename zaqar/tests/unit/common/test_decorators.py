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

import msgpack
from oslo_cache import core
from oslo_config import cfg

from zaqar.common import cache as oslo_cache
from zaqar.common import configs
from zaqar.common import decorators
from zaqar.tests import base


class TestDecorators(base.TestBase):

    def setUp(self):
        super(TestDecorators, self).setUp()
        self.conf.register_opts(configs._GENERAL_OPTIONS)

    def test_memoized_getattr(self):

        class TestClass(object):

            @decorators.memoized_getattr
            def __getattr__(self, name):
                return name

        instance = TestClass()
        result = instance.testing
        self.assertEqual('testing', result)
        self.assertIn('testing', instance.__dict__)

    def test_cached(self):
        conf = cfg.ConfigOpts()
        oslo_cache.register_config(conf)
        conf.cache.backend = 'dogpile.cache.memory'
        conf.cache.enabled = True
        cache = oslo_cache.get_cache(conf)

        sample_project = {
            u'name': u'Cats Abound',
            u'bits': b'\x80\x81\x82\x83\x84',
            b'key': u'Value. \x80',
        }

        def create_key(user, project=None):
            return user + ':' + str(project)

        class TestClass(object):

            def __init__(self, cache):
                self._cache = cache
                self.project_gets = 0
                self.project_dels = 0

            @decorators.caches(create_key, 60)
            def get_project(self, user, project=None):
                self.project_gets += 1
                return sample_project

            @get_project.purges
            def del_project(self, user, project=None):
                self.project_dels += 1

        instance = TestClass(cache)

        args = ('23', 'cats')

        project = instance.get_project(*args)
        self.assertEqual(sample_project, project)
        self.assertEqual(1, instance.project_gets)

        # Should be in the cache now.
        project = msgpack.unpackb(cache.get(create_key(*args)),
                                  encoding='utf-8')
        self.assertEqual(sample_project, project)

        # Should read from the cache this time (counter will not
        # be incremented).
        project = instance.get_project(*args)
        self.assertEqual(sample_project, project)
        self.assertEqual(1, instance.project_gets)

        # Use kwargs this time
        instance.del_project('23', project='cats')
        self.assertEqual(1, instance.project_dels)

        # Should be a cache miss since we purged (above)
        project = instance.get_project(*args)
        self.assertEqual(2, instance.project_gets)

    def test_cached_with_cond(self):
        conf = cfg.ConfigOpts()
        oslo_cache.register_config(conf)
        conf.cache.backend = 'dogpile.cache.memory'
        conf.cache.enabled = True
        cache = oslo_cache.get_cache(conf)

        class TestClass(object):

            def __init__(self, cache):
                self._cache = cache
                self.user_gets = 0

            @decorators.caches(lambda x: x, 60, lambda v: v != 'kgriffs')
            def get_user(self, name):
                self.user_gets += 1
                return name

        instance = TestClass(cache)

        name = 'malini'

        user = instance.get_user(name)
        self.assertEqual(name, user)
        self.assertEqual(1, instance.user_gets)

        # Should be in the cache now.
        user = msgpack.unpackb(cache.get(name), encoding='utf-8')
        self.assertEqual(name, user)

        # Should read from the cache this time (counter will not
        # be incremented).
        user = instance.get_user(name)
        self.assertEqual(name, user)
        self.assertEqual(1, instance.user_gets)

        # Won't go into the cache because of cond
        name = 'kgriffs'
        for i in range(3):
            user = instance.get_user(name)

            self.assertEqual(cache.get(name), core.NO_VALUE)

            self.assertEqual(name, user)
            self.assertEqual(2 + i, instance.user_gets)

    def test_api_version_manager(self):
        self.config(enable_deprecated_api_versions=[])
        # 1. Test accessing current API version
        VERSION = {
            'id': '1',
            'status': 'CURRENT',
            'updated': 'Just yesterday'
        }

        @decorators.api_version_manager(VERSION)
        def public_endpoint_1(driver, conf):
            return True

        self.assertTrue(public_endpoint_1(None, self.conf))

        # 2. Test accessing deprecated API version
        VERSION = {
            'id': '1',
            'status': 'DEPRECATED',
            'updated': 'A long time ago'
        }

        @decorators.api_version_manager(VERSION)
        def public_endpoint_2(driver, conf):
            self.fail('Deprecated API enabled')

        public_endpoint_2(None, self.conf)

        # 3. Test enabling deprecated API version
        self.config(enable_deprecated_api_versions=[['1']])

        @decorators.api_version_manager(VERSION)
        def public_endpoint_3(driver, conf):
            return True

        self.assertTrue(public_endpoint_3(None, self.conf))

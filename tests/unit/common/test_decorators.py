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
from oslo.config import cfg

from marconi.common import decorators
from marconi.openstack.common.cache import cache as oslo_cache
from marconi.tests import base


class TestDecorators(base.TestBase):

    def test_memoized_getattr(self):

        class TestClass(object):

            @decorators.memoized_getattr
            def __getattr__(self, name):
                return name

        instance = TestClass()
        result = instance.testing
        self.assertEqual(result, 'testing')
        self.assertIn('testing', instance.__dict__)

    def test_cached(self):
        conf = cfg.ConfigOpts()
        oslo_cache.register_oslo_configs(conf)
        cache = oslo_cache.get_cache(conf.cache_url)

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
        self.assertEqual(project, sample_project)
        self.assertEqual(instance.project_gets, 1)

        # Should be in the cache now.
        project = msgpack.unpackb(cache.get(create_key(*args)),
                                  encoding='utf-8')
        self.assertEqual(project, sample_project)

        # Should read from the cache this time (counter will not
        # be incremented).
        project = instance.get_project(*args)
        self.assertEqual(project, sample_project)
        self.assertEqual(instance.project_gets, 1)

        # Use kwargs this time
        instance.del_project('23', project='cats')
        self.assertEqual(instance.project_dels, 1)

        # Should be a cache miss since we purged (above)
        project = instance.get_project(*args)
        self.assertEqual(instance.project_gets, 2)

    def test_cached_with_cond(self):
        conf = cfg.ConfigOpts()
        oslo_cache.register_oslo_configs(conf)
        cache = oslo_cache.get_cache(conf.cache_url)

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
        self.assertEqual(user, name)
        self.assertEqual(instance.user_gets, 1)

        # Should be in the cache now.
        user = msgpack.unpackb(cache.get(name), encoding='utf-8')
        self.assertEqual(user, name)

        # Should read from the cache this time (counter will not
        # be incremented).
        user = instance.get_user(name)
        self.assertEqual(user, name)
        self.assertEqual(instance.user_gets, 1)

        # Won't go into the cache because of cond
        name = 'kgriffs'
        for i in range(3):
            user = instance.get_user(name)

            self.assertEqual(cache.get(name), None)

            self.assertEqual(user, name)
            self.assertEqual(instance.user_gets, 2 + i)

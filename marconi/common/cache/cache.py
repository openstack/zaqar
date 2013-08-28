# Copyright 2013 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Cache library.

Supported configuration options:

`cache_backend`: Name of the cache backend to use.
"""

from oslo.config import cfg
from stevedore import driver

_cache_options = [
    cfg.StrOpt('cache_backend',
               default='memory',
               help='The cache driver to use, default value is `memory`.'),
    cfg.StrOpt('cache_prefix',
               default=None,
               help='Prefix to use in every cache key'),
]


def get_cache(conf):
    """Loads the cache backend

    This function loads the cache backend
    specified in the given configuration.

    :param conf: Configuration instance to use
    """

    # NOTE(flaper87): oslo.config checks if options
    # exist before registering them. The code bellow
    # should be safe.
    cache_group = cfg.OptGroup(name='oslo_cache',
                               title='Cache options')

    conf.register_group(cache_group)
    conf.register_opts(_cache_options, group=cache_group)

    kwargs = dict(cache_namespace=conf.oslo_cache.cache_prefix)

    backend = conf.oslo_cache.cache_backend
    mgr = driver.DriverManager('marconi.common.cache.backends', backend,
                               invoke_on_load=True,
                               invoke_args=[conf, cache_group.name],
                               invoke_kwds=kwargs)
    return mgr.driver

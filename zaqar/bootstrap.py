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

import socket

from oslo_log import log
from osprofiler import opts as profiler_opts
from osprofiler import profiler
from stevedore import driver

from zaqar.api import handler
from zaqar.common import cache as oslo_cache
from zaqar.common import consts
from zaqar.common import decorators
from zaqar.common import errors
from zaqar.conf import drivers as driver_opts
from zaqar.conf import opts as opts_tool
from zaqar.storage import pipeline
from zaqar.storage import pooling
from zaqar.storage import utils as storage_utils
from zaqar.transport import base
from zaqar.transport.middleware import profile
from zaqar.transport import validation

LOG = log.getLogger(__name__)


class Bootstrap:
    """Defines the Zaqar bootstrapper.

    The bootstrap loads up drivers per a given configuration, and
    manages their lifetimes.
    """

    def __init__(self, conf):
        self.conf = conf

        for group, opts in opts_tool.list_opts_by_group():
            self.conf.register_opts(opts, group=group)
        profiler_opts.set_defaults(self.conf)

        # TODO(wangxiyuan): Now the OSprofiler feature in Zaqar only support
        # wsgi. Websocket part will be added in the future.
        profile.setup(self.conf, 'Zaqar-server', socket.gethostname())

        self.driver_conf = self.conf[driver_opts.GROUP_NAME]

    @decorators.lazy_property(write=False)
    def api(self):
        LOG.debug('Loading API handler')
        validate = validation.Validator(self.conf)
        defaults = base.ResourceDefaults(self.conf)
        return handler.Handler(self.storage, self.control, validate, defaults)

    @decorators.lazy_property(write=False)
    def storage(self):
        LOG.debug('Loading storage driver')
        if self.conf.pooling:
            LOG.debug('Storage pooling enabled')
            storage_driver = pooling.DataDriver(self.conf, self.cache,
                                                self.control)
            if self.conf.profiler.enabled:
                storage_driver = profiler.trace_cls("pooling_data_"
                                                    "driver")(storage_driver)
        else:
            storage_driver = storage_utils.load_storage_driver(
                self.conf, self.cache, control_driver=self.control)

        LOG.debug('Loading storage pipeline')
        return pipeline.DataDriver(self.conf, storage_driver,
                                   self.control)

    @decorators.lazy_property(write=False)
    def control(self):
        LOG.debug('Loading storage control driver')
        return storage_utils.load_storage_driver(self.conf, self.cache,
                                                 control_mode=True)

    @decorators.lazy_property(write=False)
    def cache(self):
        LOG.debug('Loading proxy cache driver')
        try:
            oslo_cache.register_config(self.conf)
            return oslo_cache.get_cache(self.conf)
        except RuntimeError as exc:
            LOG.exception('Error loading proxy cache.')
            raise errors.InvalidDriver(exc)

    @decorators.lazy_property(write=False)
    def transport(self):
        transport_name = self.driver_conf.transport
        LOG.debug('Loading transport driver: %s', transport_name)

        if transport_name == consts.TRANSPORT_WEBSOCKET:
            args = [self.conf, self.api, self.cache]
        else:
            args = [
                self.conf,
                self.storage,
                self.cache,
                self.control,
            ]

        try:
            mgr = driver.DriverManager('zaqar.transport',
                                       transport_name,
                                       invoke_on_load=True,
                                       invoke_args=args)
            return mgr.driver
        except RuntimeError as exc:
            LOG.exception('Failed to load transport driver zaqar.transport.'
                          '%(driver)s with args %(args)s',
                          {'driver': transport_name, 'args': args})
            raise errors.InvalidDriver(exc)

    def run(self):
        self.transport.listen()

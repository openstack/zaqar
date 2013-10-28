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
#
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo.config import cfg

from marconi.common import decorators
from marconi.queues import storage
from marconi.queues.storage import utils

_CATALOG_OPTIONS = [
    cfg.IntOpt('storage', default='sqlite',
               help='Catalog storage driver'),
]

_CATALOG_GROUP = 'queues:sharding:catalog'


class DataDriver(storage.DataDriverBase):
    """Sharding meta-driver for routing requests to multiple backends.

    :param storage_conf: Ignored, since this is a meta-driver
    :param catalog_conf: Options pertaining to the shard catalog
    """

    def __init__(self, conf):
        super(DataDriver, self).__init__(conf)
        self._shard_catalog = Catalog(conf)

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        return QueueController(self._shard_catalog)

    @decorators.lazy_property(write=False)
    def message_controller(self):
        return MessageController(self._shard_catalog)

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        return ClaimController(self._shard_catalog)


class RoutingController(storage.base.ControllerBase):
    """Routes operations to the appropriate shard.

    This controller stands in for a regular storage controller,
    routing operations to a driver instance that represents
    the shard to which the queue has been assigned.

    Do not instantiate this class directly; use one of the
    more specific child classes instead.
    """

    _resource_name = None

    def __init__(self, shard_catalog):
        super(RoutingController, self).__init__(None)
        self._ctrl_property_name = self._resource_name + '_controller'
        self._shard_catalog = shard_catalog

    @decorators.cached_getattr
    def __getattr__(self, name):
        # NOTE(kgriffs): Use a closure trick to avoid
        # some attr lookups each time foward() is called.
        lookup = self._shard_catalog.lookup

        # NOTE(kgriffs): Assume that every controller method
        # that is exposed to the transport declares queue name
        # as its first arg. The only exception to this
        # is QueueController.list
        def forward(queue, *args, **kwargs):
            # NOTE(kgriffs): Using .get since 'project' is an
            # optional argument.
            storage = lookup(queue, kwargs.get('project'))
            target_ctrl = getattr(storage, self._ctrl_property_name)
            return getattr(target_ctrl, name)(queue, *args, **kwargs)

        return forward


class QueueController(RoutingController):
    """Controller to facilitate special processing for queue operations."""

    _resource_name = 'queue'

    def __init__(self, shard_catalog):
        super(QueueController, self).__init__(shard_catalog)

    def list(self, project=None, marker=None,
             limit=None, detailed=False):
        # TODO(kgriffs): SHARDING - Query all shards and merge
        # the results, then return the resulting list.

        # TODO(kgriffs): Remove this placeholder code - it is
        # only here to make tests pass in the short term!
        target = self._shard_catalog.lookup(None, project).queue_controller
        return target.list(project=project, marker=marker,
                           limit=limit, detailed=detailed)

    def create(self, name, project=None):
        self._shard_catalog.register(name, project)

        target = self._shard_catalog.lookup(name, project).queue_controller
        return target.create(name, project)

    def delete(self, name, project=None):
        self._shard_catalog.deregister(name, project)

        target = self._shard_catalog.lookup(name, project).queue_controller
        return target.delete(name, project)


class MessageController(RoutingController):
    _resource_name = 'message'


class ClaimController(RoutingController):
    _resource_name = 'claim'


class Catalog(object):
    """Represents the mapping between queues and shard drivers."""

    def __init__(self, conf):
        self._shards = {}
        self._conf = conf

        self._conf.register_opts(_CATALOG_OPTIONS, group=_CATALOG_GROUP)
        self._catalog_conf = self._conf[_CATALOG_GROUP]

    def _init_shard(self, shard_id):
        # TODO(kgriffs): SHARDING - Read options from catalog backend
        conf = cfg.ConfigOpts()

        general_opts = [
            cfg.BoolOpt('admin_mode', default=False)
        ]
        options = [
            cfg.StrOpt('storage', default='sqlite'),
        ]

        conf.register_opts(general_opts)
        conf.register_opts(options, group='queues:drivers')
        return utils.load_storage_driver(conf)

    def register(self, queue, project=None):
        """Register a new queue in the shard catalog.

        This method should be called whenever a new queue is being
        created, and will create an entry in the shard catalog for
        the given queue.

        After using this method to register the queue in the
        catalog, the caller should call `lookup()` to get a reference
        to a storage driver which will allow interacting with the
        queue's assigned backend shard.

        :param queue: Name of the new queue to assign to a shard
        :param project: Project to which the queue belongs, or
            None for the "global" or "generic" project.
        """

        # TODO(kgriffs): SHARDING - Implement this!
        pass

    def deregister(self, queue, project=None):
        """Removes a queue from the shard catalog.

        Call this method after successfully deleting it from a
        backend shard.
        """

        # TODO(kgriffs): SHARDING - Implement this!
        pass

    def lookup(self, queue, project=None):
        """Lookup a shard driver for the given queue and project.

        :param queue: Name of the queue for which to find a shard
        :param project: Project to which the queue belongs, or
            None to specify the "global" or "generic" project.

        :returns: A storage driver instance for the appropriate shard. If
            the driver does not exist yet, it is created and cached.
        """

        # TODO(kgriffs): SHARDING - Raise an exception if the queue
        # does not have a mapping (it does not exist).

        # TODO(kgriffs): SHARDING - Get ID from the catalog backend
        shard_id = '[insert_id]'
        try:
            shard = self._shards[shard_id]
        except KeyError:
            self._shards[shard_id] = shard = self._init_shard(shard_id)

        return shard

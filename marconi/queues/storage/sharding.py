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

import heapq
import itertools

from oslo.config import cfg
import six

from marconi.common import decorators
from marconi.common.storage import select
from marconi.common import utils as common_utils
from marconi.openstack.common import log
from marconi.queues import storage
from marconi.queues.storage import errors
from marconi.queues.storage import utils

LOG = log.getLogger(__name__)

_CATALOG_OPTIONS = [
    cfg.IntOpt('storage', default='sqlite',
               help='Catalog storage driver'),
]

_CATALOG_GROUP = 'sharding:catalog'

# NOTE(kgriffs): E.g.: 'marconi-sharding:5083853/my-queue'
_SHARD_CACHE_PREFIX = 'sharding:'

# TODO(kgriffs): If a queue is migrated, everyone's
# caches need to have the relevant entry invalidated
# before "unfreezing" the queue, rather than waiting
# on the TTL.
#
# TODO(kgriffs): Make configurable?
_SHARD_CACHE_TTL = 10


def _shard_cache_key(queue, project=None):
    # NOTE(kgriffs): Use string concatenation for performance,
    # also put project first since it is guaranteed to be
    # unique, which should reduce lookup time.
    return _SHARD_CACHE_PREFIX + str(project) + '/' + queue


class DataDriver(storage.DataDriverBase):
    """Sharding meta-driver for routing requests to multiple backends.

    :param conf: Configuration from which to read sharding options
    :param cache: Cache instance that will be passed to individual
        storage driver instances that correspond to each shard. will
        also be used by the shard controller to reduce latency for
        some operations.
    """

    def __init__(self, conf, cache, control):
        super(DataDriver, self).__init__(conf, cache)
        self._shard_catalog = Catalog(conf, cache, control)

    def is_alive(self):
        return all(self._shard_catalog.get_driver(shard['name']).is_alive()
                   for shard in
                   self._shard_catalog._shards_ctrl.list(limit=0))

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
        # some attr lookups each time forward() is called.
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
    """Controller to facilitate special processing for queue operations.
    """

    _resource_name = 'queue'

    def __init__(self, shard_catalog):
        super(QueueController, self).__init__(shard_catalog)
        self._lookup = self._shard_catalog.lookup

    def list(self, project=None, marker=None,
             limit=None, detailed=False):

        def all_pages():
            for shard in self._shard_catalog._shards_ctrl.list(limit=0):
                yield next(self._shard_catalog.get_driver(shard['name'])
                           .queue_controller.list(
                               project=project,
                               marker=marker,
                               limit=limit,
                               detailed=detailed))

        # make a heap compared with 'name'
        ls = heapq.merge(*[
            utils.keyify('name', page)
            for page in all_pages()
        ])

        if limit is None:
            limit = self._shard_catalog._limits_conf.default_queue_paging

        marker_name = {}

        # limit the iterator and strip out the comparison wrapper
        def it():
            for queue_cmp in itertools.islice(ls, limit):
                marker_name['next'] = queue_cmp.obj['name']
                yield queue_cmp.obj

        yield it()
        yield marker_name['next']

    def create(self, name, project=None):
        self._shard_catalog.register(name, project)

        # NOTE(cpp-cabrera): This should always succeed since we just
        # registered the project/queue. There is a race condition,
        # however. If between the time we register a queue and go to
        # look it up, the queue is deleted, then this assertion will
        # fail.
        target = self._lookup(name, project)
        if not target:
            raise RuntimeError('Failed to register queue')

        return target.queue_controller.create(name, project)

    def delete(self, name, project=None):
        # NOTE(cpp-cabrera): If we fail to find a project/queue in the
        # catalogue for a delete, just ignore it.
        target = self._lookup(name, project)
        if target:

            # NOTE(cpp-cabrera): Now we found the controller. First,
            # attempt to delete it from storage. IFF the deletion is
            # successful, then remove it from the catalogue.
            control = target.queue_controller
            ret = control.delete(name, project)
            self._shard_catalog.deregister(name, project)
            return ret

        return None

    def exists(self, name, project=None, **kwargs):
        target = self._lookup(name, project)
        if target:
            control = target.queue_controller
            return control.exists(name, project=project)
        return False

    def get_metadata(self, name, project=None):
        target = self._lookup(name, project)
        if target:
            control = target.queue_controller
            return control.get_metadata(name, project=project)
        raise errors.QueueDoesNotExist(name, project)

    def set_metadata(self, name, metadata, project=None):
        target = self._lookup(name, project)
        if target:
            control = target.queue_controller
            return control.set_metadata(name, metadata=metadata,
                                        project=project)
        raise errors.QueueDoesNotExist(name, project)

    def stats(self, name, project=None):
        target = self._lookup(name, project)
        if target:
            control = target.queue_controller
            return control.stats(name, project=project)
        raise errors.QueueDoesNotExist(name, project)


class MessageController(RoutingController):
    _resource_name = 'message'

    def __init__(self, shard_catalog):
        super(MessageController, self).__init__(shard_catalog)
        self._lookup = self._shard_catalog.lookup

    def post(self, queue, project, messages, client_uuid):
        target = self._lookup(queue, project)
        if target:
            control = target.message_controller
            return control.post(queue, project=project,
                                messages=messages,
                                client_uuid=client_uuid)
        raise errors.QueueDoesNotExist(project, queue)

    def delete(self, queue, project, message_id, claim):
        target = self._lookup(queue, project)
        if target:
            control = target.message_controller
            return control.delete(queue, project=project,
                                  message_id=message_id, claim=claim)
        return None

    def bulk_delete(self, queue, project, message_ids):
        target = self._lookup(queue, project)
        if target:
            control = target.message_controller
            return control.bulk_delete(queue, project=project,
                                       message_ids=message_ids)
        return None

    def bulk_get(self, queue, project, message_ids):
        target = self._lookup(queue, project)
        if target:
            control = target.message_controller
            return control.bulk_get(queue, project=project,
                                    message_ids=message_ids)
        return []

    def list(self, queue, project, marker=None, limit=None,
             echo=False, client_uuid=None, include_claimed=False):
        target = self._lookup(queue, project)
        if target:
            control = target.message_controller
            return control.list(queue, project=project,
                                marker=marker, limit=limit,
                                echo=echo, client_uuid=client_uuid,
                                include_claimed=include_claimed)
        return iter([[]])

    def get(self, queue, message_id, project):
        target = self._lookup(queue, project)
        if target:
            control = target.message_controller
            return control.get(queue, message_id=message_id,
                               project=project)
        raise errors.QueueDoesNotExist(project, queue)


class ClaimController(RoutingController):
    _resource_name = 'claim'

    def __init__(self, shard_catalog):
        super(ClaimController, self).__init__(shard_catalog)
        self._lookup = self._shard_catalog.lookup

    def create(self, queue, metadata, project=None, limit=None):
        target = self._lookup(queue, project)
        if target:
            control = target.claim_controller
            return control.create(queue, metadata=metadata,
                                  project=project, limit=limit)
        return [None, []]

    def get(self, queue, claim_id, project):
        target = self._lookup(queue, project)
        if target:
            control = target.claim_controller
            return control.get(queue, claim_id=claim_id,
                               project=project)
        raise errors.ClaimDoesNotExist(claim_id, queue, project)

    def update(self, queue, claim_id, metadata, project):
        target = self._lookup(queue, project)
        if target:
            control = target.claim_controller
            return control.update(queue, claim_id=claim_id,
                                  project=project, metadata=metadata)
        raise errors.ClaimDoesNotExist(claim_id, queue, project)

    def delete(self, queue, claim_id, project):
        target = self._lookup(queue, project)
        if target:
            control = target.claim_controller
            return control.delete(queue, claim_id=claim_id,
                                  project=project)
        return None


class Catalog(object):
    """Represents the mapping between queues and shard drivers."""

    def __init__(self, conf, cache, control):
        self._drivers = {}
        self._conf = conf
        self._cache = cache

        self._conf.register_opts(_CATALOG_OPTIONS, group=_CATALOG_GROUP)
        self._catalog_conf = self._conf[_CATALOG_GROUP]

        self._conf.register_opts(storage.base._LIMITS_OPTIONS,
                                 group=storage.base._LIMITS_GROUP)
        self._limits_conf = self._conf[storage.base._LIMITS_GROUP]

        self._shards_ctrl = control.shards_controller
        self._catalogue_ctrl = control.catalogue_controller

    # FIXME(cpp-cabrera): https://bugs.launchpad.net/marconi/+bug/1252791
    def _init_driver(self, shard_id):
        """Given a shard name, returns a storage driver.

        :param shard_id: The name of a shard.
        :type shard_id: six.text_type
        :returns: a storage driver
        :rtype: marconi.queues.storage.base.DataDriver
        """
        shard = self._shards_ctrl.get(shard_id, detailed=True)

        # NOTE(cpp-cabrera): make it *very* clear to data storage
        # drivers that we are operating in sharding mode.
        general_dict_opts = {'dynamic': True}
        general_opts = common_utils.dict_to_conf(general_dict_opts)

        # NOTE(cpp-cabrera): parse general opts: 'drivers'
        uri = shard['uri']
        storage_type = six.moves.urllib_parse.urlparse(uri).scheme
        driver_dict_opts = {'storage': storage_type}
        driver_opts = common_utils.dict_to_conf(driver_dict_opts)

        # NOTE(cpp-cabrera): parse storage-specific opts:
        # 'drivers:storage:{type}'
        storage_dict_opts = shard['options']
        storage_dict_opts['uri'] = shard['uri']
        storage_opts = common_utils.dict_to_conf(storage_dict_opts)
        storage_group = u'drivers:storage:%s' % storage_type

        # NOTE(cpp-cabrera): register those options!
        conf = cfg.ConfigOpts()
        conf.register_opts(general_opts)
        conf.register_opts(driver_opts, group=u'drivers')
        conf.register_opts(storage_opts, group=storage_group)
        return utils.load_storage_driver(conf, self._cache)

    def _shard_id(self, queue, project=None):
        """Get the ID for the shard assigned to the given queue.

        :param queue: name of the queue
        :param project: project to which the queue belongs

        :returns: shard id

        :raises: `errors.QueueNotMapped`
        """
        cache_key = _shard_cache_key(queue, project)
        shard_id = self._cache.get(cache_key)

        if shard_id is None:
            shard_id = self._catalogue_ctrl.get(project, queue)['shard']

            if not self._cache.set(cache_key, shard_id, _SHARD_CACHE_TTL):
                LOG.warn('Failed to cache shard ID')

        return shard_id

    def _invalidate_cached_id(self, queue, project=None):
        self._cache.unset(_shard_cache_key(queue, project))

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
        :type queue: six.text_type
        :param project: Project to which the queue belongs, or
            None for the "global" or "generic" project.
        :type project: six.text_type
        :raises: NoShardFound
        """
        # NOTE(cpp-cabrera): only register a queue if the entry
        # doesn't exist
        if not self._catalogue_ctrl.exists(project, queue):
            # NOTE(cpp-cabrera): limit=0 implies unlimited - select from
            # all shards
            shard = select.weighted(self._shards_ctrl.list(limit=0))

            if not shard:
                raise errors.NoShardsFound()

            self._catalogue_ctrl.insert(project, queue, shard['name'])

    def deregister(self, queue, project=None):
        """Removes a queue from the shard catalog.

        Call this method after successfully deleting it from a
        backend shard.

        :param queue: Name of the new queue to assign to a shard
        :type queue: six.text_type
        :param project: Project to which the queue belongs, or
            None for the "global" or "generic" project.
        :type project: six.text_type
        """
        self._invalidate_cached_id(queue, project)
        self._catalogue_ctrl.delete(project, queue)

    def lookup(self, queue, project=None):
        """Lookup a shard driver for the given queue and project.

        :param queue: Name of the queue for which to find a shard
        :param project: Project to which the queue belongs, or
            None to specify the "global" or "generic" project.

        :returns: A storage driver instance for the appropriate shard. If
            the driver does not exist yet, it is created and cached. If the
            queue is not mapped, returns None.
        :rtype: Maybe DataDriver
        """

        try:
            shard_id = self._shard_id(queue, project)
        except errors.QueueNotMapped as ex:
            LOG.debug(ex)

            # NOTE(kgriffs): Return `None`, rather than letting the
            # exception bubble up, so that the higher layer doesn't
            # have to duplicate the try..except..log code all over
            # the place.
            return None

        return self.get_driver(shard_id)

    def get_driver(self, shard_id):
        """Get storage driver, preferabaly cached, fron a shard name.

        :param shard_id: The name of a shard.
        :type shard_id: six.text_type
        :returns: a storage driver
        :rtype: marconi.queues.storage.base.DataDriver
        """

        try:
            return self._drivers[shard_id]
        except KeyError:
            # NOTE(cpp-cabrera): cache storage driver connection
            self._drivers[shard_id] = self._init_driver(shard_id)

            return self._drivers[shard_id]

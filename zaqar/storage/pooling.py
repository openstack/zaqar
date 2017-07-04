# Copyright (c) 2013 Rackspace, Inc.
# Copyright 2014 Catalyst IT Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import heapq
import itertools

from oslo_config import cfg
from oslo_log import log
from osprofiler import profiler

from zaqar.common import decorators
from zaqar.common import errors as cerrors
from zaqar.common.storage import select
from zaqar import storage
from zaqar.storage import errors
from zaqar.storage import pipeline
from zaqar.storage import utils

LOG = log.getLogger(__name__)

_CATALOG_OPTIONS = (
    cfg.BoolOpt('enable_virtual_pool', default=False,
                help=('If enabled, the message_store will be used '
                      'as the storage for the virtual pool.')),
)

_CATALOG_GROUP = 'pooling:catalog'

# NOTE(kgriffs): E.g.: 'zaqar-pooling:5083853/my-queue'
_POOL_CACHE_PREFIX = 'pooling:'

# TODO(kgriffs): If a queue is migrated, everyone's
# caches need to have the relevant entry invalidated
# before "unfreezing" the queue, rather than waiting
# on the TTL.
#
# TODO(kgriffs): Make configurable?
_POOL_CACHE_TTL = 10


def _config_options():
    return [(_CATALOG_GROUP, _CATALOG_OPTIONS)]


def _pool_cache_key(queue, project=None):
    # NOTE(kgriffs): Use string concatenation for performance,
    # also put project first since it is guaranteed to be
    # unique, which should reduce lookup time.
    return _POOL_CACHE_PREFIX + str(project) + '/' + queue


class DataDriver(storage.DataDriverBase):
    """Pooling meta-driver for routing requests to multiple backends.

    :param conf: Configuration from which to read pooling options
    :param cache: Cache instance that will be passed to individual
        storage driver instances that correspond to each pool. will
        also be used by the pool controller to reduce latency for
        some operations.
    """

    BASE_CAPABILITIES = tuple(storage.Capabilities)

    def __init__(self, conf, cache, control, control_driver=None):
        super(DataDriver, self).__init__(conf, cache, control_driver)
        catalog = Catalog(conf, cache, control)
        if self.conf.profiler.enabled:
            catalog = profiler.trace_cls("pooling_catalogue_"
                                         "controller")(catalog)
        self._pool_catalog = catalog

    @property
    def capabilities(self):
        # NOTE(flaper87): We can't know the capabilities
        # of this driver because pools are loaded based on
        # the queue and project of the request. Therefore,
        # we will just assume all capabilities are supported.
        # This shouldn't be an issue because the pooling driver
        # is neither used for pools creation nor flavor creation.
        return self.BASE_CAPABILITIES

    def close(self):
        cursor = self._pool_catalog._pools_ctrl.list(limit=0)
        # Messages of each pool
        for pool in next(cursor):
            driver = self._pool_catalog.get_driver(pool['name'])
            driver.close()

    def is_alive(self):
        cursor = self._pool_catalog._pools_ctrl.list(limit=0)
        pools = next(cursor)
        return all(self._pool_catalog.get_driver(pool['name']).is_alive()
                   for pool in pools)

    def _health(self):
        KPI = {}
        # Leverage the is_alive to indicate if the backend storage is
        # reachable or not
        KPI['catalog_reachable'] = self.is_alive()

        cursor = self._pool_catalog._pools_ctrl.list(limit=0)
        # Messages of each pool
        for pool in next(cursor):
            driver = self._pool_catalog.get_driver(pool['name'])
            KPI[pool['name']] = driver._health()

        return KPI

    def gc(self):
        cursor = self._pool_catalog._pools_ctrl.list(limit=0)
        for pool in next(cursor):
            driver = self._pool_catalog.get_driver(pool['name'])
            driver.gc()

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        controller = QueueController(self._pool_catalog)
        if self.conf.profiler.enabled:
            return profiler.trace_cls("pooling_queue_controller")(controller)
        else:
            return controller

    @decorators.lazy_property(write=False)
    def message_controller(self):
        controller = MessageController(self._pool_catalog)
        if self.conf.profiler.enabled:
            return profiler.trace_cls("pooling_message_controller")(controller)
        else:
            return controller

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        controller = ClaimController(self._pool_catalog)
        if self.conf.profiler.enabled:
            return profiler.trace_cls("pooling_claim_controller")(controller)
        else:
            return controller

    @decorators.lazy_property(write=False)
    def subscription_controller(self):
        controller = SubscriptionController(self._pool_catalog)
        if self.conf.profiler.enabled:
            return (profiler.trace_cls("pooling_subscription_controller")
                    (controller))
        else:
            return controller


class QueueController(storage.Queue):
    """Routes operations to get the appropriate queue controller.

    :param pool_catalog: a catalog of available pools
    :type pool_catalog: queues.pooling.base.Catalog
    """

    def __init__(self, pool_catalog):
        super(QueueController, self).__init__(None)
        self._pool_catalog = pool_catalog
        self._mgt_queue_ctrl = self._pool_catalog.control.queue_controller
        self._get_controller = self._pool_catalog.get_queue_controller

    def _list(self, project=None, marker=None,
              limit=storage.DEFAULT_QUEUES_PER_PAGE, detailed=False):

        def all_pages():
            yield next(self._mgt_queue_ctrl.list(
                project=project,
                marker=marker,
                limit=limit,
                detailed=detailed))

        # make a heap compared with 'name'
        ls = heapq.merge(*[
            utils.keyify('name', page)
            for page in all_pages()
        ])

        marker_name = {}

        # limit the iterator and strip out the comparison wrapper
        def it():
            for queue_cmp in itertools.islice(ls, limit):
                marker_name['next'] = queue_cmp.obj['name']
                yield queue_cmp.obj

        yield it()
        yield marker_name and marker_name['next']

    def _get(self, name, project=None):
        try:
            return self.get_metadata(name, project)
        except errors.QueueDoesNotExist:
            return {}

    def _create(self, name, metadata=None, project=None):
        flavor = None
        if isinstance(metadata, dict):
            flavor = metadata.get('_flavor')

        self._pool_catalog.register(name, project=project, flavor=flavor)

        # NOTE(cpp-cabrera): This should always succeed since we just
        # registered the project/queue. There is a race condition,
        # however. If between the time we register a queue and go to
        # look it up, the queue is deleted, then this assertion will
        # fail.
        pool = self._pool_catalog.lookup(name, project)
        if not pool:
            raise RuntimeError('Failed to register queue')
        return self._mgt_queue_ctrl.create(name, metadata=metadata,
                                           project=project)

    def _delete(self, name, project=None):
        mqHandler = self._get_controller(name, project)
        if mqHandler:
            # NOTE(cpp-cabrera): delete from the catalogue first. If
            # zaqar crashes in the middle of these two operations,
            # it is desirable that the entry be missing from the
            # catalogue and present in storage, rather than the
            # reverse. The former case leads to all operations
            # behaving as expected: 404s across the board, and a
            # functionally equivalent 204 on a create queue. The
            # latter case is more difficult to reason about, and may
            # yield 500s in some operations.
            self._pool_catalog.deregister(name, project)
            mqHandler.delete(name, project)

        return self._mgt_queue_ctrl.delete(name, project)

    def _exists(self, name, project=None):
        return self._mgt_queue_ctrl.exists(name, project=project)

    def get_metadata(self, name, project=None):
        return self._mgt_queue_ctrl.get_metadata(name, project=project)

    def set_metadata(self, name, metadata, project=None):
        return self._mgt_queue_ctrl.set_metadata(name, metadata=metadata,
                                                 project=project)

    def _stats(self, name, project=None):
        mqHandler = self._get_controller(name, project)
        if mqHandler:
            return mqHandler.stats(name, project=project)
        raise errors.QueueDoesNotExist(name, project)


class MessageController(storage.Message):
    """Routes operations to a message controller in the appropriate pool.

    :param pool_catalog: a catalog of available pools
    :type pool_catalog: queues.pooling.base.Catalog
    """

    def __init__(self, pool_catalog):
        super(MessageController, self).__init__(None)
        self._pool_catalog = pool_catalog
        self._get_controller = self._pool_catalog.get_message_controller

    def post(self, queue, messages, client_uuid, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.post(queue, project=project,
                                messages=messages,
                                client_uuid=client_uuid)
        raise errors.QueueDoesNotExist(queue, project)

    def delete(self, queue, message_id, project=None, claim=None):
        control = self._get_controller(queue, project)
        if control:
            return control.delete(queue, project=project,
                                  message_id=message_id, claim=claim)
        return None

    def bulk_delete(self, queue, message_ids, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.bulk_delete(queue, project=project,
                                       message_ids=message_ids)
        return None

    def pop(self, queue, limit, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.pop(queue, project=project, limit=limit)
        return None

    def bulk_get(self, queue, message_ids, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.bulk_get(queue, project=project,
                                    message_ids=message_ids)
        return []

    def list(self, queue, project=None, marker=None,
             limit=storage.DEFAULT_MESSAGES_PER_PAGE,
             echo=False, client_uuid=None, include_claimed=False):
        control = self._get_controller(queue, project)
        if control:
            return control.list(queue, project=project,
                                marker=marker, limit=limit,
                                echo=echo, client_uuid=client_uuid,
                                include_claimed=include_claimed)
        return iter([[]])

    def get(self, queue, message_id, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.get(queue, message_id=message_id,
                               project=project)
        raise errors.QueueDoesNotExist(queue, project)

    def first(self, queue, project=None, sort=1):
        control = self._get_controller(queue, project)
        if control:
            return control.first(queue, project=project, sort=sort)
        raise errors.QueueDoesNotExist(queue, project)


class ClaimController(storage.Claim):
    """Routes operations to a claim controller in the appropriate pool.

    :param pool_catalog: a catalog of available pools
    :type pool_catalog: queues.pooling.base.Catalog
    """

    def __init__(self, pool_catalog):
        super(ClaimController, self).__init__(None)
        self._pool_catalog = pool_catalog
        self._get_controller = self._pool_catalog.get_claim_controller

    def create(self, queue, metadata, project=None,
               limit=storage.DEFAULT_MESSAGES_PER_CLAIM):
        control = self._get_controller(queue, project)
        if control:
            return control.create(queue, metadata=metadata,
                                  project=project, limit=limit)
        return [None, []]

    def get(self, queue, claim_id, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.get(queue, claim_id=claim_id,
                               project=project)
        raise errors.ClaimDoesNotExist(claim_id, queue, project)

    def update(self, queue, claim_id, metadata, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.update(queue, claim_id=claim_id,
                                  project=project, metadata=metadata)
        raise errors.ClaimDoesNotExist(claim_id, queue, project)

    def delete(self, queue, claim_id, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.delete(queue, claim_id=claim_id,
                                  project=project)
        return None


class SubscriptionController(storage.Subscription):
    """Controller to facilitate processing for subscription operations."""

    _resource_name = 'subscription'

    def __init__(self, pool_catalog):
        super(SubscriptionController, self).__init__(pool_catalog)
        self._pool_catalog = pool_catalog
        self._get_controller = self._pool_catalog.get_subscription_controller

    def list(self, queue, project=None, marker=None,
             limit=storage.DEFAULT_SUBSCRIPTIONS_PER_PAGE):
        control = self._get_controller(queue, project)
        if control:
            return control.list(queue, project=project,
                                marker=marker, limit=limit)

    def get(self, queue, subscription_id, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.get(queue, subscription_id, project=project)

    def create(self, queue, subscriber, ttl, options, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.create(queue, subscriber,
                                  ttl, options,
                                  project=project)

    def update(self, queue, subscription_id, project=None, **kwargs):
        control = self._get_controller(queue, project)
        if control:
            return control.update(queue, subscription_id,
                                  project=project, **kwargs)

    def delete(self, queue, subscription_id, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.delete(queue, subscription_id,
                                  project=project)

    def exists(self, queue, subscription_id, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.exists(queue, subscription_id,
                                  project=project)

    def confirm(self, queue, subscription_id, project=None, confirmed=None):
        control = self._get_controller(queue, project)
        if control:
            return control.confirm(queue, subscription_id,
                                   project=project, confirmed=confirmed)

    def get_with_subscriber(self, queue, subscriber, project=None):
        control = self._get_controller(queue, project)
        if control:
            return control.get_with_subscriber(queue, subscriber, project)


class Catalog(object):
    """Represents the mapping between queues and pool drivers."""

    def __init__(self, conf, cache, control):
        self._drivers = {}
        self._conf = conf
        self._cache = cache
        self.control = control

        self._conf.register_opts(_CATALOG_OPTIONS, group=_CATALOG_GROUP)
        self._catalog_conf = self._conf[_CATALOG_GROUP]

        self._pools_ctrl = control.pools_controller
        self._flavor_ctrl = control.flavors_controller
        self._catalogue_ctrl = control.catalogue_controller

    # FIXME(cpp-cabrera): https://bugs.launchpad.net/zaqar/+bug/1252791
    def _init_driver(self, pool_id, pool_conf=None):
        """Given a pool name, returns a storage driver.

        :param pool_id: The name of a pool.
        :type pool_id: six.text_type
        :returns: a storage driver
        :rtype: zaqar.storage.base.DataDriverBase
        """
        if pool_id is not None:
            pool = self._pools_ctrl.get(pool_id, detailed=True)
        else:
            pool = pool_conf
        conf = utils.dynamic_conf(pool['uri'], pool['options'],
                                  conf=self._conf)
        storage = utils.load_storage_driver(conf,
                                            self._cache,
                                            control_driver=self.control)
        return pipeline.DataDriver(conf, storage, self.control)

    @decorators.caches(_pool_cache_key, _POOL_CACHE_TTL)
    def _pool_id(self, queue, project=None):
        """Get the ID for the pool assigned to the given queue.

        :param queue: name of the queue
        :param project: project to which the queue belongs

        :returns: pool id

        :raises QueueNotMapped: if queue is not mapped
        """
        return self._catalogue_ctrl.get(project, queue)['pool']

    def register(self, queue, project=None, flavor=None):
        """Register a new queue in the pool catalog.

        This method should be called whenever a new queue is being
        created, and will create an entry in the pool catalog for
        the given queue.

        After using this method to register the queue in the
        catalog, the caller should call `lookup()` to get a reference
        to a storage driver which will allow interacting with the
        queue's assigned backend pool.

        :param queue: Name of the new queue to assign to a pool
        :type queue: six.text_type
        :param project: Project to which the queue belongs, or
            None for the "global" or "generic" project.
        :type project: six.text_type
        :param flavor: Flavor for the queue (OPTIONAL)
        :type flavor: six.text_type

        :raises NoPoolFound: if not found

        """

        # NOTE(cpp-cabrera): only register a queue if the entry
        # doesn't exist
        if not self._catalogue_ctrl.exists(project, queue):

            if flavor is not None:
                flavor = self._flavor_ctrl.get(flavor, project=project)
                pools = self._pools_ctrl.get_pools_by_group(
                    group=flavor['pool_group'],
                    detailed=True)
                pool = select.weighted(pools)
                pool = pool and pool['name'] or None
            else:
                # NOTE(flaper87): Get pools assigned to the default
                # group `None`. We should consider adding a `default_group`
                # option in the future.
                pools = self._pools_ctrl.get_pools_by_group(detailed=True)
                pool = select.weighted(pools)
                pool = pool and pool['name'] or None

                if not pool:
                    # NOTE(flaper87): We used to raise NoPoolFound in this
                    # case but we've decided to support automatic pool
                    # creation. Note that we're now returning and the queue
                    # is not being registered in the catalogue. This is done
                    # on purpose since no pool exists and the "dummy" pool
                    # doesn't exist in the storage
                    if self.lookup(queue, project) is not None:
                        return
                    raise errors.NoPoolFound()

            self._catalogue_ctrl.insert(project, queue, pool)

    @_pool_id.purges
    def deregister(self, queue, project=None):
        """Removes a queue from the pool catalog.

        Call this method after successfully deleting it from a
        backend pool.

        :param queue: Name of the new queue to assign to a pool
        :type queue: six.text_type
        :param project: Project to which the queue belongs, or
            None for the "global" or "generic" project.
        :type project: six.text_type
        """
        self._catalogue_ctrl.delete(project, queue)

    def get_queue_controller(self, queue, project=None):
        """Lookup the queue controller for the given queue and project.

        :param queue: Name of the queue for which to find a pool
        :param project: Project to which the queue belongs, or
            None to specify the "global" or "generic" project.

        :returns: The queue controller associated with the data driver for
            the pool containing (queue, project) or None if this doesn't exist.
        :rtype: Maybe QueueController
        """
        target = self.lookup(queue, project)
        return target and target.queue_controller

    def get_message_controller(self, queue, project=None):
        """Lookup the message controller for the given queue and project.

        :param queue: Name of the queue for which to find a pool
        :param project: Project to which the queue belongs, or
            None to specify the "global" or "generic" project.

        :returns: The message controller associated with the data driver for
            the pool containing (queue, project) or None if this doesn't exist.
        :rtype: Maybe MessageController
        """
        target = self.lookup(queue, project)
        return target and target.message_controller

    def get_claim_controller(self, queue, project=None):
        """Lookup the claim controller for the given queue and project.

        :param queue: Name of the queue for which to find a pool
        :param project: Project to which the queue belongs, or
            None to specify the "global" or "generic" project.

        :returns: The claim controller associated with the data driver for
            the pool containing (queue, project) or None if this doesn't exist.
        :rtype: Maybe ClaimController
        """
        target = self.lookup(queue, project)
        return target and target.claim_controller

    def get_subscription_controller(self, queue, project=None):
        """Lookup the subscription controller for the given queue and project.

        :param queue: Name of the queue for which to find a pool
        :param project: Project to which the queue belongs, or
            None to specify the "global" or "generic" project.

        :returns: The subscription controller associated with the data driver
            for the pool containing (queue, project) or None if this doesn't
            exist.
        :rtype: Maybe SubscriptionController
        """
        target = self.lookup(queue, project)
        return target and target.subscription_controller

    def get_default_pool(self, use_listing=True):
        if use_listing:
            cursor = self._pools_ctrl.list(limit=0)
            pools_list = list(next(cursor))
            if pools_list:
                return self.get_driver(pools_list[0]['name'])

        if self._catalog_conf.enable_virtual_pool:
            conf_section = ('drivers:message_store:%s' %
                            self._conf.drivers.message_store)

            try:
                # NOTE(flaper87): Try to load the driver to check
                # whether it can be used as the default store for
                # the default pool.
                utils.load_storage_driver(self._conf, self._cache,
                                          control_driver=self.control)
            except cerrors.InvalidDriver:
                # NOTE(kgriffs): Return `None`, rather than letting the
                # exception bubble up, so that the higher layer doesn't
                # have to duplicate the try..except..log code all over
                # the place.
                return None

            if conf_section not in self._conf:
                # NOTE(flaper87): If there's no config section for this storage
                # skip the pool registration entirely since we won't know how
                # to connect to it.
                return None

            # NOTE(flaper87): This assumes the storage driver type is the
            # same as the management.
            pool_conf = {'uri': self._conf[conf_section].uri,
                         'options': {}}

            # NOTE(flaper87): This will be using the config
            # storage configuration as the default one if no
            # default storage has been registered in the pool
            # store.
            return self.get_driver(None, pool_conf)

    def lookup(self, queue, project=None):
        """Lookup a pool driver for the given queue and project.

        :param queue: Name of the queue for which to find a pool
        :param project: Project to which the queue belongs, or
            None to specify the "global" or "generic" project.

        :returns: A storage driver instance for the appropriate pool. If
            the driver does not exist yet, it is created and cached. If the
            queue is not mapped, returns None.
        :rtype: Maybe DataDriver
        """

        try:
            pool_id = self._pool_id(queue, project)
        except errors.QueueNotMapped as ex:
            LOG.debug(ex)

            return self.get_default_pool(use_listing=False)

        return self.get_driver(pool_id)

    def get_driver(self, pool_id, pool_conf=None):
        """Get storage driver, preferably cached, from a pool name.

        :param pool_id: The name of a pool.
        :type pool_id: six.text_type
        :returns: a storage driver
        :rtype: zaqar.storage.base.DataDriver
        """

        try:
            return self._drivers[pool_id]
        except KeyError:
            # NOTE(cpp-cabrera): cache storage driver connection
            self._drivers[pool_id] = self._init_driver(pool_id, pool_conf)

            return self._drivers[pool_id]

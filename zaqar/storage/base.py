# Copyright (c) 2013 Red Hat, Inc.
# Copyright 2014 Catalyst IT Ltd
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

"""Implements the DriverBase abstract class for Zaqar storage drivers."""

import abc
import functools
import time

import enum
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils
import six

from zaqar.common import decorators
from zaqar.storage import errors
from zaqar.storage import utils


DEFAULT_QUEUES_PER_PAGE = 10
DEFAULT_MESSAGES_PER_PAGE = 10
DEFAULT_POOLS_PER_PAGE = 10
DEFAULT_SUBSCRIPTIONS_PER_PAGE = 10

DEFAULT_MESSAGES_PER_CLAIM = 10

LOG = logging.getLogger(__name__)


@enum.unique
class Capabilities(enum.IntEnum):
    """Enum of storage capabilities."""
    FIFO = 1
    CLAIMS = 2
    DURABILITY = 3
    AOD = 4  # At least once delivery
    HIGH_THROUGHPUT = 5


@six.add_metaclass(abc.ABCMeta)
class DriverBase(object):
    """Base class for both data and control plane drivers

    :param conf: Configuration containing options for this driver.
    :type conf: `oslo_config.ConfigOpts`
    :param cache: Cache instance to use for reducing latency
        for certain lookups.
    :type cache: `dogpile.cache.region.CacheRegion`
    """
    _DRIVER_OPTIONS = []

    def __init__(self, conf, cache):
        self.conf = conf
        self.cache = cache
        self._register_opts()

    def _register_opts(self):
        for group, options in self._DRIVER_OPTIONS:
            for opt in options:
                try:
                    self.conf.register_opt(opt, group=group)
                except cfg.DuplicateOptError:
                    pass


@six.add_metaclass(abc.ABCMeta)
class DataDriverBase(DriverBase):
    """Interface definition for storage drivers.

    Data plane storage drivers are responsible for implementing the
    core functionality of the system.

    Connection information and driver-specific options are
    loaded from the config file or the pool catalog.

    :param conf: Configuration containing options for this driver.
    :type conf: `oslo_config.ConfigOpts`
    :param cache: Cache instance to use for reducing latency
        for certain lookups.
    :type cache: `dogpile.cache.region.CacheRegion`
    """

    BASE_CAPABILITIES = []

    def __init__(self, conf, cache, control_driver):
        super(DataDriverBase, self).__init__(conf, cache)
        # creating ControlDriver instance for accessing QueueController's
        # data from DataDriver
        self.control_driver = control_driver

    @abc.abstractmethod
    def is_alive(self):
        """Check whether the storage is ready."""
        raise NotImplementedError

    @abc.abstractproperty
    def capabilities(self):
        """Returns storage's capabilities."""
        return self.BASE_CAPABILITIES

    def health(self):
        """Return the health status of service."""
        overall_health = {}
        # NOTE(flwang): KPI extracted from different storage backends,
        # _health() will be implemented by different storage drivers.
        backend_health = self._health()
        if backend_health:
            overall_health.update(backend_health)

        return overall_health

    @abc.abstractmethod
    def _health(self):
        """Return the health status based on different backends."""
        raise NotImplementedError

    @abc.abstractmethod
    def close(self):
        """Close connections to the backend."""
        raise NotImplementedError

    def _get_operation_status(self):
        op_status = {}
        status_template = lambda s, t, r: {'succeeded': s,
                                           'seconds': t,
                                           'ref': r}
        project = uuidutils.generate_uuid()
        queue = uuidutils.generate_uuid()
        client = uuidutils.generate_uuid()
        msg_template = lambda s: {'ttl': 600, 'body': {'event': 'p_%s' % s}}
        messages = [msg_template(i) for i in range(100)]
        claim_metadata = {'ttl': 60, 'grace': 300}

        # NOTE (flwang): Using time.time() instead of timeit since timeit will
        # make the method calling be complicated.
        def _handle_status(operation_type, callable_operation):
            succeeded = True
            ref = None
            result = None
            try:
                start = time.time()
                result = callable_operation()
            except Exception as e:
                ref = uuidutils.generate_uuid()
                LOG.exception(e, extra={'instance_uuid': ref})
                succeeded = False
            status = status_template(succeeded, time.time() - start, ref)
            op_status[operation_type] = status
            return succeeded, result

        # create queue
        func = functools.partial(self.queue_controller.create,
                                 queue, project=project)
        succeeded, _ = _handle_status('create_queue', func)

        # post messages
        if succeeded:
            func = functools.partial(self.message_controller.post,
                                     queue, messages, client, project=project)
            _, msg_ids = _handle_status('post_messages', func)

            # claim messages
            if msg_ids:
                func = functools.partial(self.claim_controller.create,
                                         queue, claim_metadata,
                                         project=project)
                _, (claim_id, claim_msgs) = _handle_status('claim_messages',
                                                           func)

                # list messages
                func = functools.partial(self.message_controller.list,
                                         queue, project, echo=True,
                                         client_uuid=client,
                                         include_claimed=True)
                _handle_status('list_messages', func)

                # delete messages
                if claim_id and claim_msgs:
                    for message in claim_msgs:
                        func = functools.partial(self.
                                                 message_controller.delete,
                                                 queue, message['id'],
                                                 project, claim=claim_id)
                        succeeded, _ = _handle_status('delete_messages', func)
                        if not succeeded:
                            break
                    # delete claim
                    func = functools.partial(self.claim_controller.delete,
                                             queue, claim_id, project)
                    _handle_status('delete_claim', func)

            # delete queue
            func = functools.partial(self.message_controller.bulk_delete,
                                     queue, msg_ids, project=project)
            _handle_status('bulk_delete_messages', func)
            func = functools.partial(self.queue_controller.delete,
                                     queue, project=project)
            _handle_status('delete_queue', func)
        return op_status

    def gc(self):
        """Perform manual garbage collection of claims and messages.

        This method can be overridden in order to provide a trigger
        that can be called by so-called "garbage collection" scripts
        that are required by some drivers.

        By default, this method does nothing.
        """
        pass

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        return self.control_driver.queue_controller

    @abc.abstractproperty
    def message_controller(self):
        """Returns the driver's message controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def claim_controller(self):
        """Returns the driver's claim controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def subscription_controller(self):
        """Returns the driver's subscription controller."""
        raise NotImplementedError


@six.add_metaclass(abc.ABCMeta)
class ControlDriverBase(DriverBase):
    """Interface definition for control plane storage drivers.

    Storage drivers that work at the control plane layer allow one to
    modify aspects of the functionality of the system. This is ideal
    for administrative purposes.

    Allows access to the pool registry through a catalogue and a
    pool controller.

    :param conf: Configuration containing options for this driver.
    :type conf: `oslo_config.ConfigOpts`
    :param cache: Cache instance to use for reducing latency
        for certain lookups.
    :type cache: `dogpile.cache.region.CacheRegion`
    """

    @abc.abstractproperty
    def catalogue_controller(self):
        """Returns the driver's catalogue controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def pools_controller(self):
        """Returns storage's pool management controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def flavors_controller(self):
        """Returns storage's flavor management controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def queue_controller(self):
        """Returns the driver's queue controller."""
        raise NotImplementedError

    @abc.abstractmethod
    def close(self):
        """Close connections to the backend."""
        raise NotImplementedError


class ControllerBase(object):
    """Top-level class for controllers.

    :param driver: Instance of the driver
        instantiating this controller.
    """

    def __init__(self, driver):
        self.driver = driver


@six.add_metaclass(abc.ABCMeta)
class Queue(ControllerBase):
    """This class is responsible for managing queues.

    Queue operations include CRUD, monitoring, etc.

    Storage driver implementations of this class should
    be capable of handling high workloads and huge
    numbers of queues.
    """

    def list(self, project=None, marker=None,
             limit=DEFAULT_QUEUES_PER_PAGE, detailed=False):
        """Base method for listing queues.

        :param project: Project id
        :param marker: The last queue name
        :param limit: (Default 10) Max number of queues to return
        :param detailed: Whether metadata is included

        :returns: An iterator giving a sequence of queues
            and the marker of the next page.
        """
        return self._list(project, marker, limit, detailed)

    _list = abc.abstractmethod(lambda x: None)

    def get(self, name, project=None):
        """Base method for queue metadata retrieval.

        :param name: The queue name
        :param project: Project id

        :returns: Dictionary containing queue metadata
        :raises DoesNotExist: if queue metadata does not exist
        """
        return self._get(name, project)

    _get = abc.abstractmethod(lambda x: None)

    def get_metadata(self, name, project=None):
        """Base method for queue metadata retrieval.

        :param name: The queue name
        :param project: Project id

        :returns: Dictionary containing queue metadata
        :raises DoesNotExist: if queue metadata does not exist
        """
        raise NotImplementedError

    def set_metadata(self, name, metadata, project=None):
        """Base method for updating a queue metadata.

        :param name: The queue name
        :param metadata: Queue metadata as a dict
        :param project: Project id
        :raises DoesNotExist: if queue metadata can not be updated
        """
        raise NotImplementedError

    def create(self, name, metadata=None, project=None):
        """Base method for queue creation.

        :param name: The queue name
        :param project: Project id
        :returns: True if a queue was created and False
            if it was updated.
        """
        return self._create(name, metadata, project)

    _create = abc.abstractmethod(lambda x: None)

    def exists(self, name, project=None):
        """Base method for testing queue existence.

        :param name: The queue name
        :param project: Project id
        :returns: True if a queue exists and False
            if it does not.
        """
        return self._exists(name, project)

    _exists = abc.abstractmethod(lambda x: None)

    def delete(self, name, project=None):
        """Base method for deleting a queue.

        :param name: The queue name
        :param project: Project id
        """
        return self._delete(name, project)

    _delete = abc.abstractmethod(lambda x: None)

    def stats(self, name, project=None):
        """Base method for queue stats.

        :param name: The queue name
        :param project: Project id
        :returns: Dictionary with the
            queue stats
        """
        return self._stats(name, project)

    _stats = abc.abstractmethod(lambda x: None)


@six.add_metaclass(abc.ABCMeta)
class Message(ControllerBase):
    """This class is responsible for managing message CRUD."""

    @abc.abstractmethod
    def list(self, queue, project=None, marker=None,
             limit=DEFAULT_MESSAGES_PER_PAGE,
             echo=False, client_uuid=None,
             include_claimed=False):
        """Base method for listing messages.

        :param queue: Name of the queue to get the
            message from.
        :param project: Project id
        :param marker: Tail identifier
        :param limit: (Default 10) Max number of messages to return.
        :type limit: Maybe int
        :param echo: (Default False) Boolean expressing whether
            or not this client should receive its own messages.
        :param client_uuid: A UUID object. Required when echo=False.
        :param include_claimed: omit claimed messages from listing?
        :type include_claimed: bool

        :returns: An iterator giving a sequence of messages and
            the marker of the next page.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def first(self, queue, project=None, sort=1):
        """Get first message in the queue (including claimed).

        :param queue: Name of the queue to list
        :param sort: (Default 1) Sort order for the listing. Pass 1 for
            ascending (oldest message first), or -1 for descending (newest
            message first).

        :returns: First message in the queue, or None if the queue is
            empty
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, queue, message_id, project=None):
        """Base method for getting a message.

        :param queue: Name of the queue to get the
            message from.
        :param project: Project id
        :param message_id: Message ID

        :returns: Dictionary containing message data
        :raises DoesNotExist: if message data can not be got
        """
        raise NotImplementedError

    @abc.abstractmethod
    def bulk_get(self, queue, message_ids, project=None):
        """Base method for getting multiple messages.

        :param queue: Name of the queue to get the
            message from.
        :param project: Project id
        :param message_ids: A sequence of message IDs.

        :returns: An iterable, yielding dicts containing
            message details
        """
        raise NotImplementedError

    @abc.abstractmethod
    def post(self, queue, messages, client_uuid, project=None):
        """Base method for posting one or more messages.

        Implementations of this method should guarantee
        and preserve the order, in the returned list, of
        incoming messages.

        :param queue: Name of the queue to post message to.
        :param messages: Messages to post to queue, an iterable
            yielding 1 or more elements. An empty iterable
            results in undefined behavior.
        :param client_uuid: A UUID object.
        :param project: Project id

        :returns: List of message ids
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, queue, message_id, project=None, claim=None):
        """Base method for deleting a single message.

        :param queue: Name of the queue to post
            message to.
        :param message_id: Message to be deleted
        :param project: Project id
        :param claim: Claim this message
            belongs to. When specified, claim must
            be valid and message_id must belong to
            it.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def bulk_delete(self, queue, message_ids, project=None):
        """Base method for deleting multiple messages.

        :param queue: Name of the queue to post
            message to.
        :param message_ids: A sequence of message IDs
            to be deleted.
        :param project: Project id
        """
        raise NotImplementedError

    @abc.abstractmethod
    def pop(self, queue, limit, project=None):
        """Base method for popping messages.

        :param queue: Name of the queue to pop
            message from.
        :param limit: Number of messages to pop.
        :param project: Project id
        """
        raise NotImplementedError


@six.add_metaclass(abc.ABCMeta)
class Claim(ControllerBase):

    @abc.abstractmethod
    def get(self, queue, claim_id, project=None):
        """Base method for getting a claim.

        :param queue: Name of the queue this
            claim belongs to.
        :param claim_id: The claim id
        :param project: Project id

        :returns: (Claim's metadata, claimed messages)
        :raises DoesNotExist: if claimed messages can not be got
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, queue, metadata, project=None,
               limit=DEFAULT_MESSAGES_PER_CLAIM):
        """Base method for creating a claim.

        :param queue: Name of the queue this
            claim belongs to.
        :param metadata: Claim's parameters
            to be stored.
        :param project: Project id
        :param limit: (Default 10) Max number
            of messages to claim.

        :returns: (Claim ID, claimed messages)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, queue, claim_id, metadata, project=None):
        """Base method for updating a claim.

        :param queue: Name of the queue this
            claim belongs to.
        :param claim_id: Claim to be updated
        :param metadata: Claim's parameters
            to be updated.
        :param project: Project id
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, queue, claim_id, project=None):
        """Base method for deleting a claim.

        :param queue: Name of the queue this
            claim belongs to.
        :param claim_id: Claim to be deleted
        :param project: Project id
        """
        raise NotImplementedError


@six.add_metaclass(abc.ABCMeta)
class Subscription(ControllerBase):
    """This class is responsible for managing subscriptions of notification.

    """

    @abc.abstractmethod
    def list(self, queue, project=None, marker=None,
             limit=DEFAULT_SUBSCRIPTIONS_PER_PAGE):
        """Base method for listing subscriptions.

        :param queue: Name of the queue to get the subscriptions from.
        :type queue: six.text_type
        :param project: Project this subscription belongs to.
        :type project: six.text_type
        :param marker: used to determine which subscription to start with
        :type marker: six.text_type
        :param limit: (Default 10) Max number of results to return
        :type limit: int
        :returns: An iterator giving a sequence of subscriptions
            and the marker of the next page.
        :rtype: [{}]
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, queue, subscription_id, project=None):
        """Returns a single subscription entry.

        :param queue: Name of the queue subscription belongs to.
        :type queue: six.text_type
        :param subscription_id: ID of this subscription
        :type subscription_id: six.text_type
        :param project: Project this subscription belongs to.
        :type project: six.text_type
        :returns: Dictionary containing subscription data
        :rtype: {}
        :raises SubscriptionDoesNotExist: if not found
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, queue, subscriber, ttl, options, project=None):
        """Create a new subscription.

        :param queue:The source queue for notifications
        :type queue: six.text_type
        :param subscriber: The subscriber URI
        :type subscriber: six.text_type
        :param ttl: time to live for this subscription
        :type ttl: int
        :param options: Options used to configure this subscription
        :type options: dict
        :param project: Project id
        :type project: six.text_type
        :returns: True if a subscription was created and False
        if it is failed.
        :rtype: boolean
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, queue, subscription_id, project=None, **kwargs):
        """Updates the weight, uris, and/or options of this subscription

        :param queue: Name of the queue subscription belongs to.
        :type queue: six.text_type
        :param name: ID of the subscription
        :type name: text
        :param kwargs: one of: `source`, `subscriber`, `ttl`, `options`
        :type kwargs: dict
        :raises SubscriptionDoesNotExist: if not found
        :raises SubscriptionAlreadyExists: if attempt to update in a way to
            create duplicate subscription
        """

        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, queue, subscription_id, project=None):
        """Base method for testing subscription existence.

        :param queue: Name of the queue subscription belongs to.
        :type queue: six.text_type
        :param subscription_id: ID of subscription
        :type subscription_id: six.text_type
        :param project: Project id
        :type project: six.text_type
        :returns: True if a subscription exists and False
            if it does not.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, queue, subscription_id, project=None):
        """Base method for deleting a subscription.

        :param queue: Name of the queue subscription belongs to.
        :type queue: six.text_type
        :param subscription_id: ID of the subscription to be deleted.
        :type subscription_id: six.text_type
        :param project: Project id
        :type project: six.text_type
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_with_subscriber(self, queue, subscriber, project=None):
        """Base method for get a subscription with the subscriber.

        :param queue: Name of the queue subscription belongs to.
        :type queue: six.text_type
        :param subscriber: link of the subscription to be notified.
        :type subscriber: six.text_type
        :param project: Project id
        :type project: six.text_type
        :returns: Dictionary containing subscription data
        :rtype: dict
        """
        raise NotImplementedError

    @abc.abstractmethod
    def confirm(self, queue, subscription_id, project=None, confirmed=True):
        """Base method for confirming a subscription.

        :param queue: Name of the queue subscription belongs to.
        :type queue: six.text_type
        :param subscription_id: ID of the subscription to be deleted.
        :type subscription_id: six.text_type
        :param project: Project id
        :type project: six.text_type
        :param confirmed: Confirm a subscription or cancel the confirmation of
            a subscription.
        :type confirmed: boolean
        """
        raise NotImplementedError


@six.add_metaclass(abc.ABCMeta)
class PoolsBase(ControllerBase):
    """A controller for managing pools."""

    def _check_capabilities(self, uri, group=None, name=None):
        default_store = self.driver.conf.drivers.message_store
        pool_caps = self.capabilities(group=group, name=name)

        if not pool_caps:
            return True

        new_store = utils.load_storage_impl(uri,
                                            default_store=default_store)

        # NOTE(flaper87): Since all pools in a pool group
        # are assumed to have the same capabilities, it's
        # fine to check against just 1
        return pool_caps == new_store.BASE_CAPABILITIES

    def capabilities(self, group=None, name=None):
        """Gets the set of capabilities for this group/name

        :param group: The pool group to get capabilities for
        :type group: six.text_type
        :param name: The pool name to get capabilities for
        :type name: six.text_type
        """
        if name:
            group = list(self._get_pools_by_group(self._get(name)['group']))
        else:
            group = list(self._get_pools_by_group(group))

        if not len(group) > 0:
            return ()

        default_store = self.driver.conf.drivers.message_store

        pool_store = utils.load_storage_impl(group[0]['uri'],
                                             default_store=default_store)

        return pool_store.BASE_CAPABILITIES

    def list(self, marker=None, limit=DEFAULT_POOLS_PER_PAGE,
             detailed=False):
        """Lists all registered pools.

        :param marker: used to determine which pool to start with
        :type marker: six.text_type
        :param limit: (Default 10) Max number of results to return
        :type limit: int
        :param detailed: whether to include options
        :type detailed: bool
        :returns: A list of pools - name, weight, uri
        :rtype: [{}]
        """

        return self._list(marker, limit, detailed)

    _list = abc.abstractmethod(lambda x: None)

    def create(self, name, weight, uri, group=None, options=None):
        """Registers a pool entry.

        :param name: The name of this pool
        :type name: six.text_type
        :param weight: the likelihood that this pool will be used
        :type weight: int
        :param uri: A URI that can be used by a storage client
            (e.g., pymongo) to access this pool.
        :type uri: six.text_type
        :param group: The group of this pool
        :type group: six.text_type
        :param options: Options used to configure this pool
        :type options: dict
        """
        if not self._check_capabilities(uri, group=group):
            raise errors.PoolCapabilitiesMismatch()

        return self._create(name, weight, uri, group, options)

    _create = abc.abstractmethod(lambda x: None)

    def get_pools_by_group(self, group=None, detailed=False):
        """Returns a pool list filtered by given pool group.

        :param group: The group to filter on. `None` returns
            pools that are not assigned to any pool group.
        :type group: six.text_type
        :param detailed: Should the options data be included?
        :type detailed: bool
        :returns: weight, uri, and options for this pool
        :rtype: {}
        :raises PoolDoesNotExist: if not found
        """
        return self._get_pools_by_group(group, detailed)

    _get_pools_by_group = abc.abstractmethod(lambda x: None)

    def get(self, name, detailed=False):
        """Returns a single pool entry.

        :param name: The name of this pool
        :type name: six.text_type
        :param detailed: Should the options data be included?
        :type detailed: bool
        :returns: weight, uri, and options for this pool
        :rtype: {}
        :raises PoolDoesNotExist: if not found
        """
        return self._get(name, detailed)

    _get = abc.abstractmethod(lambda x: None)

    def exists(self, name):
        """Returns a single pool entry.

        :param name: The name of this pool
        :type name: six.text_type
        :returns: True if the pool exists
        :rtype: bool
        """
        return self._exists(name)

    _exists = abc.abstractmethod(lambda x: None)

    def delete(self, name):
        """Removes a pool entry.

        :param name: The name of this pool
        :type name: six.text_type
        :rtype: None
        """
        return self._delete(name)

    _delete = abc.abstractmethod(lambda x: None)

    def update(self, name, **kwargs):
        """Updates the weight, uris, and/or options of this pool

        :param name: Name of the pool
        :type name: text
        :param kwargs: one of: `uri`, `weight`, `options`
        :type kwargs: dict
        :raises PoolDoesNotExist: if not found
        """
        uri = kwargs.get('uri')
        if uri and not self._check_capabilities(uri, name=name):
            raise errors.PoolCapabilitiesMismatch()

        return self._update(name, **kwargs)

    _update = abc.abstractmethod(lambda x: None)

    def drop_all(self):
        """Deletes all pools from storage."""
        return self._drop_all()

    _drop_all = abc.abstractmethod(lambda x: None)


@six.add_metaclass(abc.ABCMeta)
class CatalogueBase(ControllerBase):
    """A controller for managing the catalogue.

    The catalogue is responsible for maintaining a mapping
    between project.queue entries to their pool.
    """

    @abc.abstractmethod
    def list(self, project):
        """Get a list of queues from the catalogue.

        :param project: The project to use when filtering through queue
                        entries.
        :type project: six.text_type
        :returns: [{'project': ..., 'queue': ..., 'pool': ...},]
        :rtype: [dict]
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get(self, project, queue):
        """Returns the pool identifier for the given queue.

        :param project: Namespace to search for the given queue
        :type project: six.text_type
        :param queue: The name of the queue to search for
        :type queue: six.text_type
        :returns: {'pool': ...}
        :rtype: dict
        :raises QueueNotMapped: if queue is not mapped
        """

        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, project, queue):
        """Determines whether the given queue exists under project.

        :param project: Namespace to check.
        :type project: six.text_type
        :param queue: str - Particular queue to check for
        :type queue: six.text_type
        :return: True if the queue exists under this project
        :rtype: bool
        """

    @abc.abstractmethod
    def insert(self, project, queue, pool):
        """Creates a new catalogue entry, or updates it if it already exists.

        :param project: str - Namespace to insert the given queue into
        :type project: six.text_type
        :param queue: str - The name of the queue to insert
        :type queue: six.text_type
        :param pool: pool identifier to associate this queue with
        :type pool: six.text_type
        """

        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, project, queue):
        """Removes this entry from the catalogue.

        :param project: The namespace to search for this queue
        :type project: six.text_type
        :param queue: The queue name to remove
        :type queue: six.text_type
        """

        raise NotImplementedError

    @abc.abstractmethod
    def update(self, project, queue, pools=None):
        """Updates the pool identifier for this queue.

        :param project: Namespace to search
        :type project: six.text_type
        :param queue: The name of the queue
        :type queue: six.text_type
        :param pools: The name of the pool where this project/queue lives.
        :type pools: six.text_type
        :raises QueueNotMapped: if queue is not mapped
        """

        raise NotImplementedError

    @abc.abstractmethod
    def drop_all(self):
        """Drops all catalogue entries from storage."""

        raise NotImplementedError


@six.add_metaclass(abc.ABCMeta)
class FlavorsBase(ControllerBase):
    """A controller for managing flavors."""

    @abc.abstractmethod
    def list(self, project=None, marker=None, limit=10):
        """Lists all registered flavors.

        :param project: Project this flavor belongs to.
        :type project: six.text_type
        :param marker: used to determine which flavor to start with
        :type marker: six.text_type
        :param limit: (Default 10) Max number of results to return
        :type limit: int
        :returns: A list of flavors - name, project, flavor
        :rtype: [{}]
        """

        raise NotImplementedError

    @abc.abstractmethod
    def create(self, name, pool, project=None, capabilities=None):
        """Registers a flavor entry.

        :param name: The name of this flavor
        :type name: six.text_type
        :param project: Project this flavor belongs to.
        :type project: six.text_type
        :param pool: The name of the pool to use for this flavor.
        :type pool: six.text_type
        :param capabilities: Flavor capabilities
        :type capabilities: dict
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get(self, name, project=None):
        """Returns a single flavor entry.

        :param name: The name of this flavor
        :type name: six.text_type
        :param project: Project this flavor belongs to.
        :type project: six.text_type
        :rtype: {}
        :raises FlavorDoesNotExist: if not found
        """

        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, name, project=None):
        """Verifies whether the flavor exists.

        :param name: The name of this flavor
        :type name: six.text_type
        :param project: Project this flavor belongs to.
        :type project: six.text_type
        :returns: True if the flavor exists
        :rtype: bool
        """

        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, name, project=None):
        """Removes a flavor entry.

        :param name: The name of this flavor
        :type name: six.text_type
        :param project: Project this flavor belongs to.
        :type project: six.text_type
        :rtype: None
        """

        raise NotImplementedError

    @abc.abstractmethod
    def update(self, name, project=None, **kwargs):
        """Updates the flavor and/or capabilities of this flavor

        :param name: Name of the flavor
        :type name: text
        :param project: Project this flavor belongs to.
        :type project: six.text_type
        :param kwargs: one of: `uri`, `weight`, `options`
        :type kwargs: dict
        :raises FlavorDoesNotExist: if not found
        """

        raise NotImplementedError

    @abc.abstractmethod
    def drop_all(self):
        """Deletes all flavors from storage."""

        raise NotImplementedError

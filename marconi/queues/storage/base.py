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

"""Implements the DriverBase abstract class for Marconi storage drivers."""

import abc

import six

DEFAULT_QUEUES_PER_PAGE = 10
DEFAULT_MESSAGES_PER_PAGE = 10
DEFAULT_POOLS_PER_PAGE = 10

DEFAULT_MESSAGES_PER_CLAIM = 10


@six.add_metaclass(abc.ABCMeta)
class DriverBase(object):
    """Base class for both data and control plane drivers

    :param conf: Configuration containing options for this driver.
    :type conf: `oslo.config.ConfigOpts`
    :param cache: Cache instance to use for reducing latency
        for certain lookups.
    :type cache: `marconi.openstack.common.cache.backends.BaseCache`
    """
    def __init__(self, conf, cache):
        self.conf = conf
        self.cache = cache


@six.add_metaclass(abc.ABCMeta)
class DataDriverBase(DriverBase):
    """Interface definition for storage drivers.

    Data plane storage drivers are responsible for implementing the
    core functionality of the system.

    Connection information and driver-specific options are
    loaded from the config file or the pool catalog.

    :param conf: Configuration containing options for this driver.
    :type conf: `oslo.config.ConfigOpts`
    :param cache: Cache instance to use for reducing latency
        for certain lookups.
    :type cache: `marconi.openstack.common.cache.backends.BaseCache`
    """

    def __init__(self, conf, cache):
        super(DataDriverBase, self).__init__(conf, cache)

    @abc.abstractmethod
    def is_alive(self):
        """Check whether the storage is ready."""
        raise NotImplementedError

    @abc.abstractproperty
    def queue_controller(self):
        """Returns the driver's queue controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def message_controller(self):
        """Returns the driver's message controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def claim_controller(self):
        """Returns the driver's claim controller."""
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
    :type conf: `oslo.config.ConfigOpts`
    :param cache: Cache instance to use for reducing latency
        for certain lookups.
    :type cache: `marconi.openstack.common.cache.backends.BaseCache`
    """

    @abc.abstractproperty
    def catalogue_controller(self):
        """Returns the driver's catalogue controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def pools_controller(self):
        """Returns storage's pool management controller."""
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

    @abc.abstractmethod
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
        raise NotImplementedError

    @abc.abstractmethod
    def get_metadata(self, name, project=None):
        """Base method for queue metadata retrieval.

        :param name: The queue name
        :param project: Project id

        :returns: Dictionary containing queue metadata
        :raises: DoesNotExist
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, name, project=None):
        """Base method for queue creation.

        :param name: The queue name
        :param project: Project id
        :returns: True if a queue was created and False
            if it was updated.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, name, project=None):
        """Base method for testing queue existence.

        :param name: The queue name
        :param project: Project id
        :returns: True if a queue exists and False
            if it does not.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_metadata(self, name, metadata, project=None):
        """Base method for updating a queue metadata.

        :param name: The queue name
        :param metadata: Queue metadata as a dict
        :param project: Project id
        :raises: DoesNotExist
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, name, project=None):
        """Base method for deleting a queue.

        :param name: The queue name
        :param project: Project id
        """
        raise NotImplementedError

    @abc.abstractmethod
    def stats(self, name, project=None):
        """Base method for queue stats.

        :param name: The queue name
        :param project: Project id
        :returns: Dictionary with the
            queue stats
        """
        raise NotImplementedError


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
        :raises: DoesNotExist
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
        :raises: DoesNotExist
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
class PoolsBase(ControllerBase):
    """A controller for managing pools."""

    @abc.abstractmethod
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
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, name, weight, uri, options=None):
        """Registers a pool entry.

        :param name: The name of this pool
        :type name: six.text_type
        :param weight: the likelihood that this pool will be used
        :type weight: int
        :param uri: A URI that can be used by a storage client
        (e.g., pymongo) to access this pool.
        :type uri: six.text_type
        :param options: Options used to configure this pool
        :type options: dict
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, name, detailed=False):
        """Returns a single pool entry.

        :param name: The name of this pool
        :type name: six.text_type
        :param detailed: Should the options data be included?
        :type detailed: bool
        :returns: weight, uri, and options for this pool
        :rtype: {}
        :raises: PoolDoesNotExist if not found
        """
        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, name):
        """Returns a single pool entry.

        :param name: The name of this pool
        :type name: six.text_type
        :returns: True if the pool exists
        :rtype: bool
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, name):
        """Removes a pool entry.

        :param name: The name of this pool
        :type name: six.text_type
        :rtype: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, name, **kwargs):
        """Updates the weight, uris, and/or options of this pool

        :param name: Name of the pool
        :type name: text
        :param kwargs: one of: `uri`, `weight`, `options`
        :type kwargs: dict
        :raises: PoolDoesNotExist
        """
        raise NotImplementedError

    @abc.abstractmethod
    def drop_all(self):
        """Deletes all pools from storage."""
        raise NotImplementedError


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
        :raises: QueueNotMapped
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
        :raises: QueueNotMapped
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
    def list(self, project=None, marker=None, limit=10, detailed=False):
        """Lists all registered flavors.

        :param project: Project this flavor belongs to.
        :type project: six.text_type
        :param marker: used to determine which flavor to start with
        :type marker: six.text_type
        :param limit: (Default 10) Max number of results to return
        :type limit: int
        :param detailed: whether to include capabilities
        :type detailed: bool
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
    def get(self, name, project=None, detailed=False):
        """Returns a single flavor entry.

        :param name: The name of this flavor
        :type name: six.text_type
        :param project: Project this flavor belongs to.
        :type project: six.text_type
        :param detailed: Should the options data be included?
        :type detailed: bool
        :rtype: {}
        :raises: FlavorDoesNotExist if not found
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
        :raises: FlavorDoesNotExist
        """
        raise NotImplementedError

    @abc.abstractmethod
    def drop_all(self):
        """Deletes all flavors from storage."""
        raise NotImplementedError

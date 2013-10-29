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

from oslo.config import cfg

_LIMITS_OPTIONS = [
    cfg.IntOpt('default_queue_paging', default=10,
               help='Default queue pagination size'),

    cfg.IntOpt('default_message_paging', default=10,
               help='Default message pagination size')
]

_LIMITS_GROUP = 'limits:storage'


@six.add_metaclass(abc.ABCMeta)
class DriverBase(object):
    """Base class for both data and control plane drivers

    :param conf: Configuration containing options for this driver.
    :type conf: `oslo.config.ConfigOpts`
    :param cache: Cache instance to use for reducing latency
        for certain lookups.
    :type cache: `marconi.common.cache.backends.BaseCache`
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
    loaded from the config file or the shard catalog.

    :param conf: Configuration containing options for this driver.
    :type conf: `oslo.config.ConfigOpts`
    :param cache: Cache instance to use for reducing latency
        for certain lookups.
    :type cache: `marconi.common.cache.backends.BaseCache`
    """

    def __init__(self, conf, cache):
        super(DataDriverBase, self).__init__(conf, cache)

        self.conf.register_opts(_LIMITS_OPTIONS, group=_LIMITS_GROUP)
        self.limits_conf = self.conf[_LIMITS_GROUP]

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

    Allows access to the shard registry through a catalogue and a
    shard controller.

    :param conf: Configuration containing options for this driver.
    :type conf: `oslo.config.ConfigOpts`
    :param cache: Cache instance to use for reducing latency
        for certain lookups.
    :type cache: `marconi.common.cache.backends.BaseCache`
    """

    @abc.abstractproperty
    def catalogue_controller(self):
        """Returns the driver's catalogue controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def shards_controller(self):
        """Returns storage's shard management controller."""
        raise NotImplementedError


class ControllerBase(object):
    """Top-level class for controllers.

    :param driver: Instance of the driver
        instantiating this controller.
    """

    def __init__(self, driver):
        self.driver = driver


@six.add_metaclass(abc.ABCMeta)
class QueueBase(ControllerBase):
    """This class is responsible for managing queues.

    Queue operations include CRUD, monitoring, etc.

    Storage driver implementations of this class should
    be capable of handling high workloads and huge
    numbers of queues.
    """

    @abc.abstractmethod
    def list(self, project=None, marker=None,
             limit=None, detailed=False):
        """Base method for listing queues.

        :param project: Project id
        :param marker: The last queue name
        :param limit: (Default 10, configurable) Max number
            queues to return.
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
class MessageBase(ControllerBase):
    """This class is responsible for managing message CRUD."""

    @abc.abstractmethod
    def list(self, queue, project=None, marker=None,
             limit=None, echo=False, client_uuid=None,
             include_claimed=False):
        """Base method for listing messages.

        :param queue: Name of the queue to get the
            message from.
        :param project: Project id
        :param marker: Tail identifier
        :param limit: (Default 10, configurable) Max number
            messages to return.
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

        :returns: An iterable, yielding dicts containing message details
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


@six.add_metaclass(abc.ABCMeta)
class ClaimBase(ControllerBase):

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
    def create(self, queue, metadata, project=None, limit=None):
        """Base method for creating a claim.

        :param queue: Name of the queue this
            claim belongs to.
        :param metadata: Claim's parameters
            to be stored.
        :param project: Project id
        :param limit: (Default 10, configurable) Max number
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
class ShardsBase(ControllerBase):
    """A controller for managing shards."""

    @abc.abstractmethod
    def list(self, marker=None, limit=10, detailed=False):
        """Lists all registered shards.

        :param marker: used to determine which shard to start with
        :type marker: six.text_type
        :param limit: how many results to return
        :type limit: int
        :param detailed: whether to include options
        :type detailed: bool
        :returns: A list of shards - name, weight, uri
        :rtype: [{}]
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, name, weight, uri, options=None):
        """Registers a shard entry.

        :param name: The name of this shard
        :type name: six.text_type
        :param weight: the likelihood that this shard will be used
        :type weight: int
        :param uri: A URI that can be used by a storage client
        (e.g., pymongo) to access this shard.
        :type uri: six.text_type
        :param options: Options used to configure this shard
        :type options: dict
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, name, detailed=False):
        """Returns a single shard entry.

        :param name: The name of this shard
        :type name: six.text_type
        :param detailed: Should the options data be included?
        :type detailed: bool
        :returns: weight, uri, and options for this shard
        :rtype: {}
        :raises: ShardDoesNotExist if not found
        """
        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, name):
        """Returns a single shard entry.

        :param name: The name of this shard
        :type name: six.text_type
        :returns: True if the shard exists
        :rtype: bool
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, name):
        """Removes a shard entry.

        :param name: The name of this shard
        :type name: six.text_type
        :rtype: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, name, **kwargs):
        """Updates the weight, uris, and/or options of this shard

        :param name: Name of the shard
        :type name: text
        :param kwargs: one of: `uri`, `weight`, `options`
        :type kwargs: dict
        :raises: ShardDoesNotExist
        """
        raise NotImplementedError

    @abc.abstractmethod
    def drop_all(self):
        """Deletes all shards from storage."""
        raise NotImplementedError


@six.add_metaclass(abc.ABCMeta)
class CatalogueBase(ControllerBase):
    """A controller for managing the catalogue. The catalogue is
    responsible for maintaining a mapping between project.queue
    entries to their shard.
    """

    @abc.abstractmethod
    def list(self, project):
        """Returns a list of queue entries from the catalogue associated with
        this project.

        :param project: The project to use when filtering through queue
                        entries.
        :type project: six.text_type
        :returns: [{'project': ..., 'queue': ..., 'shard': ...},]
        :rtype: [dict]
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, project, queue):
        """Returns the shard identifier for the queue registered under this
        project.

        :param project: Namespace to search for the given queue
        :type project: six.text_type
        :param queue: The name of the queue to search for
        :type queue: six.text_type
        :returns: {'shard': ...}
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
    def insert(self, project, queue, shard):
        """Creates a new catalogue entry, or updates it if it already existed.

        :param project: str - Namespace to insert the given queue into
        :type project: six.text_type
        :param queue: str - The name of the queue to insert
        :type queue: six.text_type
        :param shard: shard identifier to associate this queue with
        :type shard: six.text_type
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
    def update(self, project, queue, shards=None):
        """Updates the shard identifier for this queue

        :param project: Namespace to search
        :type project: six.text_type
        :param queue: The name of the queue
        :type queue: six.text_type
        :param shards: The name of the shard where this project/queue lives.
        :type shards: six.text_type
        :raises: QueueNotMapped
        """
        raise NotImplementedError

    @abc.abstractmethod
    def drop_all(self):
        """Drops all catalogue entries from storage."""
        raise NotImplementedError

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

_LIMITS_GROUP = 'queues:limits:storage'


@six.add_metaclass(abc.ABCMeta)
class DataDriverBase(object):
    """Interface definition for storage drivers.

    Data plane storage drivers are responsible for implementing the
    core functionality of the system.

    Connection information and driver-specific options are
    loaded from the config file or the shard catalog.

    :param conf: Driver configuration. Can be any
        dict-like object containing the expected
        options. Must at least include 'uri' which
        provides connection options such as host and
        port.

    """

    def __init__(self, conf):
        self.conf = conf

        self.conf.register_opts(_LIMITS_OPTIONS, group=_LIMITS_GROUP)
        self.limits_conf = self.conf[_LIMITS_GROUP]

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
class ControlDriverBase(object):
    """Interface definition for control plane storage drivers.

    Storage drivers that work at the control plane layer allow one to
    modify aspects of the functionality of the system. This is ideal
    for administrative purposes.

    Allows access to the shard registry through a catalogue and a
    shard controller.

    """

    def __init__(self, conf):
        self.conf = conf

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
    def list(self, project=None, marker=None, limit=10,
             detailed=False, include_claimed=True):
        """Base method for listing queues.

        :param project: Project id
        :param marker: The last queue name
        :param limit: (Default 10, configurable) Max number
            queues to return.
        :param detailed: Whether metadata is included
        :param include_claimed: Whether to list claimed messages

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
             limit=10, echo=False, client_uuid=None):
        """Base method for listing messages.

        :param queue: Name of the queue to get the
            message from.
        :param project: Project id
        :param marker: Tail identifier
        :param limit: (Default 10, configurable) Max number
            messages to return.
        :param echo: (Default False) Boolean expressing whether
            or not this client should receive its own messages.
        :param client_uuid: A UUID object. Required when echo=False.

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
    def create(self, queue, metadata, project=None, limit=10):
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


class AdminControllerBase(object):
    """Top-level class for controllers.

    :param driver: Instance of the driver
        instantiating this controller.
    """

    def __init__(self, driver):
        self.driver = driver


@six.add_metaclass(abc.ABCMeta)
class ShardsBase(AdminControllerBase):
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

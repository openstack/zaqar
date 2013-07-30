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


class DriverBase:
    __metaclass__ = abc.ABCMeta

    def gc(self):
        """Runs a garbage collection operation.

        Called periodically by mongo-gc to trigger removal
        of expired resources from the storage provider.

        If GC is supported by a given driver, the driver
        MUST override this method.
        """
        raise NotImplementedError

    @property
    def gc_interval(self):
        """Returns the GC interval, in seconds.

        Used by mongo-gc to determine how often to
        call driver.gc().

        If GC is supported by a given driver, the driver
        MUST override this method.
        """
        raise NotImplementedError

    @abc.abstractproperty
    def queue_controller(self):
        """Returns storage's queues controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def message_controller(self):
        """Returns storage's messages controller."""
        raise NotImplementedError

    @abc.abstractproperty
    def claim_controller(self):
        """Returns storage's claims controller."""
        raise NotImplementedError


class ControllerBase(object):
    """Top-level class for controllers.

    :param driver: Instance of the driver
        instantiating this controller.
    """

    def __init__(self, driver):
        self.driver = driver


class QueueBase(ControllerBase):
    """This class is responsible for managing queues.

    Queue operations include CRUD, monitoring, etc.

    Storage driver implementations of this class should
    be capable of handling high workloads and huge
    numbers of queues.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def list(self, project=None, marker=None, limit=10,
             detailed=False, include_claimed=True):
        """Base method for listing queues.

        :param project: Project id
        :param marker: The last queue name
        :param limit: (Default 10) Max number
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
        """Base method for queue creation

        :param name: The queue name
        :param project: Project id
        :returns: True if a queue was created and False
            if it was updated.
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

    @abc.abstractmethod
    def actions(self, name, project=None, marker=None, limit=10):
        """Base method for queue actions.

        :param name: Queue name
        :param project: Project id
        :param marker: Tail identifier
        :param limit: (Default 10) Max number
            of messages to retrieve.
        """
        raise NotImplementedError


class MessageBase(ControllerBase):
    """This class is responsible for managing message CRUD."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def list(self, queue, project=None, marker=None,
             limit=10, echo=False, client_uuid=None):
        """Base method for listing messages.

        :param queue: Name of the queue to get the
            message from.
        :param project: Project id
        :param marker: Tail identifier
        :param limit: (Default 10) specifies up to 100
            messages to return.
        :param echo: (Default False) Boolean expressing whether
            or not this client should receive its own messages.
        :param client_uuid: Client's unique identifier. This param
            is required when echo=False.

        :returns: An iterator giving a sequence of messages and
            the marker of the next page.
        """
        raise NotImplementedError

    def get(self, queue, message_ids, project=None):
        """Base method for getting a message.

        :param queue: Name of the queue to get the
            message from.
        :param project: Project id
        :param message_ids: One message ID or a
            sequence of message IDs.

        :returns: An iterable, yielding dicts containing message details
        :raises: DoesNotExist
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
        :param client_uuid: Client's unique identifier.
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


class ClaimBase(ControllerBase):

    __metaclass__ = abc.ABCMeta

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

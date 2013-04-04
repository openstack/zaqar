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

    @abc.abstractproperty
    def queue_controller(self):
        """
        Returns storage's queues controller
        """
        raise NotImplementedError

    @abc.abstractproperty
    def message_controller(self):
        """
        Returns storage's messages controller
        """
        raise NotImplementedError

    @abc.abstractproperty
    def claim_controller(self):
        """
        Returns storage's claims controller
        """
        raise NotImplementedError


class ControllerBase(object):
    """
    Top level class for controllers.

    :param driver: Instance of the driver
        instantiating this controller.
    """

    def __init__(self, driver):
        self.driver = driver


class QueueBase(ControllerBase):
    """
    This class is responsible of managing
    queues which means handling their CRUD
    operations, monitoring and interactions.

    Storages' implementations of this class
    should be capable of handling high work
    loads and huge number of queues.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def list(self, tenant=None):
        """
        Base method for listing queues.

        :param tenant: Tenant id

        :returns: List of queues
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, name, tenant=None):
        """
        Base method for queue retrieval.

        :param name: The queue name
        :param tenant: Tenant id

        :returns: Dictionary containing queue metadata
        :raises: DoesNotExist
        """
        raise NotImplementedError

    @abc.abstractmethod
    def upsert(self, name, metadata, tenant=None):
        """
        This methods handles both creates and updates
        operations for queues.

        :param name: The queue name
        :param metadata: Arbitrary metadata
        :param tenant: Tenant id
        :returns: True if a queue was created and False
            if it was updated.
        """
        msg = _("Metadata should be an instance of dict")
        assert isinstance(metadata, dict), msg

    @abc.abstractmethod
    def delete(self, name, tenant=None):
        """
        Base method for queue deletion.

        :param name: The queue name
        :param tenant: Tenant id
        """
        raise NotImplementedError

    @abc.abstractmethod
    def stats(self, name, tenant=None):
        """
        Base method for queue stats.

        :param name: The queue name
        :param tenant: Tenant id
        :returns: Dictionary with the
            queue stats
        """
        raise NotImplementedError

    @abc.abstractmethod
    def actions(self, name, tenant=None, marker=None, limit=10):
        """
        Base method for queue actions.

        :param name: Queue name
        :param tenant: Tenant id
        :param marker: Tail identifier
        :param limit: (Default 10) Max number
            of messages to retrieve.
        """
        raise NotImplementedError


class MessageBase(ControllerBase):
    """
    This class is responsible for managing
    messages CRUD.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def list(self, queue, tenant=None, marker=None,
             limit=10, echo=False, client_uuid=None):
        """
        Base message list method

        :param queue: Name of the queue to get the
            message from.
        :param tenant: Tenant id
        :param marker: Tail identifier
        :param limit: (Default 10) specifies up to 100
            messages to return.
        :param echo: (Default False) Boolean expressing whether
            or not this client should receive its own messages.
        :param client_uuid: Client's unique identifier. This param
            is required when echo=False.

        :returns: Iterator of messages
        """
        raise NotImplementedError

    def get(self, queue, message_id, tenant=None):
        """
        Base message get method

        :param queue: Name of the queue to get the
            message from.
        :param tenant: Tenant id
        :param message_id: Message ID

        :returns: Dictionary containing message data
        :raises: DoesNotExist
        """
        raise NotImplementedError

    @abc.abstractmethod
    def post(self, queue, messages, tenant=None, client_uuid=None):
        """
        Base message post method

        Implementations of this method should guarantee
        and preserve the order, in the returned list, of
        incoming messages.

        :param queue: Name of the queue to post message to.
        :param messages: Messages to post to queue,
            it can be a list of 1 or more elements.
        :param tenant: Tenant id
        :param client_uuid: Client's unique identifier.

        :returns: List of message ids
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, queue, message_id, tenant=None, claim=None):
        """
        Base message delete method

        :param queue: Name of the queue to post
            message to.
        :param message_id: Message to be deleted
        :param tenant: Tenant id
        :param claim: Claim this message
            belongs to. When specified, claim must
            be valid and message_id must belong to
            it.
        """
        raise NotImplementedError


class ClaimBase(ControllerBase):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get(self, queue, claim_id, tenant=None):
        """
        Base claim get method

        :param queue: Name of the queue this
            claim belongs to.
        :param claim_id: The claim id
        :param tenant: Tenant id

        :returns: Dictionary containing claim's
            metadata and claimed messages.
        :raises: DoesNotExist
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, queue, metadata, tenant=None, limit=10):
        """
        Base claim create method

        :param queue: Name of the queue this
            claim belongs to.
        :param metadata: Claim's parameters
            to be stored.
        :param tenant: Tenant id
        :param limit: (Default 10) Max number
            of messages to claim.

        :returns: Dictionary containing claim's
            metadata and claimed messages.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, queue, claim_id, metadata, tenant=None):
        """
        Base claim update method

        :param queue: Name of the queue this
            claim belongs to.
        :param claim_id: Claim to be updated
        :param metadata: Claim's parameters
            to be updated.
        :param tenant: Tenant id
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, queue, claim_id, tenant=None):
        """
        Base claim delete method

        :param queue: Name of the queue this
            claim belongs to.
        :param claim_id: Claim to be deleted
        :param tenant: Tenant id
        """
        raise NotImplementedError

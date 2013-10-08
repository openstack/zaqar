# Copyright (c) 2013 Rackspace Hosting, Inc.
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

"""Defines an interface for working with proxy partitions and the catalogue."""

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class DriverBase(object):
    @abc.abstractproperty
    def partitions_controller(self):
        """Returns proxy storage's controller for registering
        and removing partitions.
        """
        raise NotImplementedError

    @abc.abstractproperty
    def catalogue_controller(self):
        """Returns proxy storage's controller for modifying catalogue
        entries.
        """
        raise NotImplementedError


class ControllerBase(object):
    """Top-level class for controllers.

    :param driver: Instance of the driver
        instantiating this controller.
    """

    def __init__(self, driver):
        self.driver = driver


@six.add_metaclass(abc.ABCMeta)
class PartitionsBase(ControllerBase):
    """A controller for managing partitions."""

    @abc.abstractmethod
    def list(self):
        """Lists all partitions registered by this driver.
        :returns: A list of partitions, including: weight, name,
                  and a list of nodes associated with that partition.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, name):
        """Retrieves the nodes and weight for a partition with this name.

        :param name: The name the partition was registered with.
        :raises: PartitionNotFound
        """
        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, name):
        """Determines whether the given partition exists

        :param name: str - Partition name to check for
        :return: True | False
        """

    @abc.abstractmethod
    def create(self, name, weight, nodes):
        """Registers a new partition.

        :param name: The name given to this partition
        :param weight: An integer representing how often to select from this
                       partition when making load balancing decisions.
        :param nodes: A list of URLs of nodes associated with this partition
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, name):
        """Removes a partition from storage."""
        raise NotImplementedError

    @abc.abstractmethod
    def drop_all(self):
        """Drops all partitions from storage."""
        raise NotImplementedError

    def update(self, name, **kwargs):
        """Updates the weight and/or hosts of this partition.

        :param name: Name of the partition
        :type name: text
        :param weight: Weight, > 0
        :type weight: int
        :param kwargs: one of 'hosts' or 'weight'
        :type kwargs: dict
        :raises: PartitionNotFound, AssertionError
        """
        raise NotImplementedError


@six.add_metaclass(abc.ABCMeta)
class CatalogueBase(ControllerBase):
    """A controller for managing the catalogue. The catalogue is
    responsible for maintaining a mapping between project.queue entries to
    their name, location href, and their metadata.

    It's expected that this controller will have to handle many of
    these mappings. Ideally, an implementation of this controller will
    attempt to keep storage compact. Furthermore, in a scalable
    Marconi deployment where the proxy is used, this controller will
    be responsible for providing the data needed to implement queue
    listings. Therefore, it should be able to efficiently list all
    queues associated with a particular project ID.
    """

    @abc.abstractmethod
    def list(self, project):
        """Returns a list of queue entries from the catalogue associated with
        this project.

        :param project: The project to use when filtering through queue
                        entries.
        :returns: a list of dicts: [{'name': ., 'location': ., 'metadata': .}]
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, project, queue):
        """Returns the name, metadata, and location for the queue
        registered under this project.

        :param project: Namespace to search for the given queue
        :param queue: The name of the queue to search for
        :returns: a dict, {'name': ., 'location': ., 'metadata': .}
        :raises: EntryNotFound
        """
        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, project, queue):
        """Determines whether the given queue exists under project.

        :param project: str - Namespace to check.
        :param queue: str - Particular queue to check for
        :return: True | False
        """

    @abc.abstractmethod
    def insert(self, project, queue, partition, host, metadata={}):
        """Creates a new catalogue entry.

        :param project: str - Namespace to insert the given queue into
        :param queue: str - The name of the queue to insert
        :param partition: str - Partition name where this queue is stored
        :param host: text - URL to representative host
        :param metadata: A dictionary of metadata for this queue
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, project, queue):
        """Removes this entry from the catalogue.

        :param project: The namespace to search for this queue
        :param queue: The queue name to remove
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_metadata(self, project, queue, metadata):
        """Updates the metadata associated with this queue.

        :param project: Namespace to search
        :param queue: The name of the queue
        :param metadata: A dictionary of metadata for this queue
        """
        raise NotImplementedError

    @abc.abstractmethod
    def drop_all(self):
        """Drops all catalogue entries from storage."""
        raise NotImplementedError

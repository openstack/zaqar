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
"""lookup: functions to handle caching/lookup of proxy details."""
import msgpack

from marconi.openstack.common import log
from marconi.proxy.storage import exceptions

LOG = log.getLogger(__name__)

def _entry_key(project, queue):
    assert project is not None, 'Project must not be None'
    assert queue is not None, 'Queue must not be None'
    return 'q:' + project + '/' + queue


def _partition_key(name):
    return 'p:' + name


def try_cache_entry(project, queue, catalogue_controller, cache):
    """Attempts to cache a given project/queue's partition name.

    :param project: the project namespace
    :type project: text
    :param queue: the name of the queue
    :type queue: text
    :param catalogue_controller: primary storage for the queue catalogue
    :type catalogue_controller: marconi.proxy.storage.base:Catalogue*
    :param cache: cache for catalogue - updated if lookup fails
    :type cache: marconi.common.cache.backends:BaseCache
    :returns: partition name or None if not found
    :rtype: text | None
    """
    key = _entry_key(project, queue)
    name = None

    try:
        name = catalogue_controller.get(project, queue)['partition']
    except exceptions.EntryNotFound:
        LOG.debug('CACHE entry - project/queue: {0}/{1}'.format(
            project, queue
        ))

        return None

    cache.set(key, name)

    return name


def exists(project, queue, catalogue_controller, cache):
    """Checks whether a given project/queue exists.

    :param project: the project namespace
    :type project: text
    :param queue: the name of the queue
    :type queue: text
    :param catalogue_controller: primary storage for the queue catalogue
    :type catalogue_controller: marconi.proxy.storage.base:Catalogue*
    :param cache: cache for catalogue - updated if lookup fails
    :type cache: marconi.common.cache.backends:BaseCache
    :returns: True or False
    :rtype: bool
    """
    key = _entry_key(project, queue)

    if not cache.has_key(key):  # flake8: noqa
        return try_cache_entry(project, queue,
                               catalogue_controller, cache) is not None

    return True


def invalidate_entry(project, queue, cache):
    """Removes an entry from the cache."""
    LOG.debug('INVALIDATE entry - project/queue: {0}/{1}'.format(
        project, queue
    ))

    key = _entry_key(project, queue)
    cache.unset(key)


def partition(project, queue, catalogue_controller, cache):
    """Returns the name of the partition associated with this project.queue

    :param project: text - the project namespace
    :type project: text
    :param queue: text - the name of the queue
    :type queue: text
    :param catalogue_controller: primary storage for the queue catalogue
    :type catalogue_controller: marconi.proxy.storage.base:Catalogue*
    :param cache: cache for catalogue - updated if lookup fails
    :type cache: marconi.common.cache.backends:BaseCache
    :returns: partition name or None if not found
    :rtype: text | None
    """
    LOG.debug('LOOKUP partition - project/queue: {0}/{1}'.format(
        project, queue
    ))

    key = _entry_key(project, queue)
    name = cache.get(key)

    if not name:
        LOG.debug('Entry not in cache: ' + key)
        return try_cache_entry(project, queue,
                               catalogue_controller, cache)

    return name


def invalidate_partition(name, cache):
    """Removes a partition from the cache."""
    LOG.debug('INVALIDATE partition - partition: ' + name)

    key = _partition_key(name)
    cache.unset(key)


def hosts(name, partitions_controller, cache):
    """Returns the list of hosts associated with this partition.

    :param name: text - the name of the partition to look up
    :param partitions_controller: handler for primary storage
    :param cache: cache to check first - updated if partition not found
    :returns: Maybe [text] - list of hosts or None if not found
    """
    LOG.debug('LOOKUP hosts - partition: ' + name)

    key = _partition_key(name)
    data = cache.get(key)
    hosts = None

    if data:
        hosts = msgpack.loads(data)

    if not hosts:
        LOG.debug('Partition not in cache: ' + name)

        try:
            hosts = partitions_controller.get(name)['hosts']
        except exceptions.PartitionNotFound:
            LOG.debug('Partition not in primary storage: ' + name)
            return None

        cache.set(key, msgpack.dumps(hosts))

    return hosts

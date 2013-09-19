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

from marconi.proxy.storage import exceptions


def partition(project, queue, catalogue_controller, cache):
    """Returns the name of the partition associated with this project.queue

    :param project: text - the project namespace
    :param queue: text - the name of the queue
    :param catalogue_controller: primary storage for the queue catalogue
    :param cache: cache for catalogue - updated if lookup fails
    :returns: Maybe text - partition name or None if not found
    """
    key = u'q.{project}.{queue}'.format(project=project, queue=queue)
    name = cache.get(key)
    if not name:
        try:
            name = catalogue_controller.get(project, queue)['partition']
        except exceptions.EntryNotFound:
            return None
        cache.set(key, name)

    return name


def hosts(name, partitions_controller, cache):
    """Returns the list of hosts associated with this partition.

    :param name: text - the name of the partition to look up
    :param partitions_controller: handler for primary storage
    :param cache: cache to check first - updated if partition not found
    :returns: Maybe [text] - list of hosts or None if not found
    """
    key = u'p.{name}'.format(name=name)
    data = cache.get(key)
    hosts = None

    if data:
        hosts = msgpack.loads(data)

    if not hosts:
        try:
            hosts = partitions_controller.get(name)['hosts']
        except exceptions.PartitionNotFound:
            return None
        cache.set(key, msgpack.dumps(hosts))

    return hosts

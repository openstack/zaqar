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

"""These are the exceptions that the proxy storage layer can raise."""


class NotFound(Exception):
    pass


class EntryNotFound(NotFound):
    """An exception thrown when a catalogue entry is expected
    but not found.
    """
    def __init__(self, project, queue):
        msg = 'Catalogue entry {project}.{queue} was not found'.format(
            project=project, queue=queue
        )
        super(EntryNotFound, self).__init__(msg)


class PartitionNotFound(NotFound):
    """An exception thrown when a partition is expected
    but not found.
    """
    def __init__(self, name):
        msg = 'Partition {name} was not found'.format(
            name=name
        )
        super(PartitionNotFound, self).__init__(msg)

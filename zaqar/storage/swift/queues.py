# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import functools

from oslo_serialization import jsonutils
import swiftclient

from zaqar import storage
from zaqar.storage import errors
from zaqar.storage.swift import utils


class QueueController(storage.Queue):
    """Implements queue resource operations with swift backend.

    Queues are scoped by project.

    queue -> Swift mapping:
       +----------------+---------------------------------------+
       | Attribute      | Storage location                      |
       +----------------+---------------------------------------+
       | Queue Name     | Object name                           |
       +----------------+---------------------------------------+
       | Project name   | Container name prefix                 |
       +----------------+---------------------------------------+
       | Created time   | Object Creation Time                  |
       +----------------+---------------------------------------+
       | Queue metadata | Object content                        |
       +----------------+---------------------------------------+
    """

    def __init__(self, *args, **kwargs):
        super(QueueController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection

    def _list(self, project=None, marker=None,
              limit=storage.DEFAULT_QUEUES_PER_PAGE, detailed=False):
        container = utils._queue_container(project)
        try:
            _, objects = self._client.get_container(container,
                                                    limit=limit,
                                                    marker=marker)
        except swiftclient.ClientException as exc:
            if exc.http_status == 404:
                self._client.put_container(container)
                objects = []
            else:
                raise
        marker_next = {}
        yield utils.QueueListCursor(
            objects, detailed, marker_next,
            functools.partial(self._client.get_object, container))
        yield marker_next and marker_next['next']

    def _get(self, name, project=None):
        try:
            return self.get_metadata(name, project)
        except errors.QueueDoesNotExist:
            return {}

    def get_metadata(self, name, project=None):
        container = utils._queue_container(project)
        try:
            _, metadata = self._client.get_object(container, name)
        except swiftclient.ClientException as exc:
            if exc.http_status == 404:
                raise errors.QueueDoesNotExist(name, project)
            else:
                raise
        return jsonutils.loads(metadata) or {}

    def set_metadata(self, name, metadata, project=None):
        self._create(name, metadata, project)

    def _create(self, name, metadata=None, project=None):
        try:
            utils._put_or_create_container(
                self._client, utils._queue_container(project), name,
                content_type='application/json',
                contents=jsonutils.dumps(metadata),
                headers={'if-none-match': '*'})
        except swiftclient.ClientException as exc:
            if exc.http_status == 412:
                if metadata:
                    # Enforce metadata setting regardless
                    utils._put_or_create_container(
                        self._client, utils._queue_container(project), name,
                        content_type='application/json',
                        contents=jsonutils.dumps(metadata))
                return False
            raise
        else:
            return True

    def _delete(self, name, project=None):
        try:
            self._client.delete_object(utils._queue_container(project), name)
        except swiftclient.ClientException as exc:
            if exc.http_status != 404:
                raise

    def _stats(self, name, project=None):
        pass

    def _exists(self, name, project=None):
        try:
            return self._client.head_object(utils._queue_container(project),
                                            name)
        except swiftclient.ClientException as exc:
            if exc.http_status != 404:
                raise
            return False
        else:
            return True

# Copyright (c) 2013 Rackspace, Inc.
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

from marconi.queues import storage


class DataDriver(storage.DataDriverBase):
    def __init__(self, conf, cache):
        super(DataDriver, self).__init__(conf, cache)

    @property
    def default_options(self):
        return {}

    def is_alive(self):
        raise NotImplementedError()

    @property
    def queue_controller(self):
        return QueueController(self)

    @property
    def message_controller(self):
        return MessageController(self)

    @property
    def claim_controller(self):
        return None


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)

    @property
    def catalogue_controller(self):
        return None

    @property
    def shards_controller(self):
        return None


class QueueController(storage.QueueBase):
    def __init__(self, driver):
        pass

    def list(self, project=None):
        raise NotImplementedError()

    def get_metadata(self, name, project=None):
        raise NotImplementedError()

    def create(self, name, project=None):
        raise NotImplementedError()

    def exists(self, name, project=None):
        raise NotImplementedError()

    def set_metadata(self, name, metadata, project=None):
        raise NotImplementedError()

    def delete(self, name, project=None):
        raise NotImplementedError()

    def stats(self, name, project=None):
        raise NotImplementedError()


class MessageController(storage.MessageBase):
    def __init__(self, driver):
        pass

    def first(self, queue_name, project=None, sort=1):
        raise NotImplementedError()

    def get(self, queue, message_id, project=None):
        raise NotImplementedError()

    def bulk_get(self, queue, message_ids, project=None):
        raise NotImplementedError()

    def list(self, queue, project=None, marker=None,
             limit=None, echo=False, client_uuid=None):
        raise NotImplementedError()

    def post(self, queue, messages, project=None):
        raise NotImplementedError()

    def delete(self, queue, message_id, project=None, claim=None):
        raise NotImplementedError()

    def bulk_delete(self, queue, message_ids, project=None):
        raise NotImplementedError()

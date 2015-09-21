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

from oslo_config import cfg

from zaqar import storage

_CONFIG_GROUP = 'drivers:message_store:faulty'


class DataDriver(storage.DataDriverBase):

    _DRIVER_OPTIONS = [(_CONFIG_GROUP,
                        [cfg.StrOpt('uri', default='faulty://')])]

    def __init__(self, conf, cache, control_driver):
        super(DataDriver, self).__init__(conf, cache, control_driver)

    def close(self):
        pass

    @property
    def default_options(self):
        return {}

    @property
    def capabilities(self):
        raise NotImplementedError()

    def is_alive(self):
        raise NotImplementedError()

    def _health(self):
        raise NotImplementedError()

    @property
    def queue_controller(self):
        return self.control_driver.queue_controller

    @property
    def message_controller(self):
        return MessageController(self)

    @property
    def claim_controller(self):
        return None

    @property
    def subscription_controller(self):
        return None


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)

    def close(self):
        pass

    @property
    def queue_controller(self):
        return QueueController(self)

    @property
    def catalogue_controller(self):
        return None

    @property
    def pools_controller(self):
        return None

    @property
    def flavors_controller(self):
        return None


class QueueController(storage.Queue):
    def __init__(self, driver):
        pass

    def _list(self, project=None):
        raise NotImplementedError()

    def _get(self, name, project=None):
        raise NotImplementedError()

    def get_metadata(self, name, project=None):
        raise NotImplementedError()

    def _create(self, name, metadata=None, project=None):
        raise NotImplementedError()

    def _exists(self, name, project=None):
        raise NotImplementedError()

    def set_metadata(self, name, metadata, project=None):
        raise NotImplementedError()

    def _delete(self, name, project=None):
        raise NotImplementedError()

    def _stats(self, name, project=None):
        raise NotImplementedError()


class MessageController(storage.Message):
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

    def pop(self, queue, pop_limit, project=None):
        raise NotImplementedError()

    def delete(self, queue, message_id, project=None, claim=None):
        raise NotImplementedError()

    def bulk_delete(self, queue, message_ids, project=None):
        raise NotImplementedError()

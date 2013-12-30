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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import sqlalchemy as sa

from oslo.config import cfg

from marconi.common import decorators
from marconi.queues import storage
from marconi.queues.storage.sqlalchemy import tables


_SQLALCHEMY_OPTIONS = [
    cfg.StrOpt('database', default=':memory:',
               help='Sqlalchemy database to use.')
]

_SQLALCHEMY_GROUP = 'drivers:storage:sqlalchemy'


class DataDriver(storage.DataDriverBase):

    def __init__(self, conf, cache):
        super(DataDriver, self).__init__(conf, cache)

        self.conf.register_opts(_SQLALCHEMY_OPTIONS, group=_SQLALCHEMY_GROUP)
        self.sqlalchemy_conf = self.conf[_SQLALCHEMY_GROUP]

        self.__path = self.sqlalchemy_conf.database

    @decorators.lazy_property(write=False)
    def engine(self, *args, **kwargs):
        engine = sa.create_engine(*args, **kwargs)
        tables.metadata.create_all(engine, checkfirst=True)
        return engine

    @decorators.lazy_property(write=False)
    def connection(self):
        return self.engine.connect()

    def close_connection(self):
        self.connection.close()

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        return None

    @decorators.lazy_property(write=False)
    def message_controller(self):
        return None

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        return None

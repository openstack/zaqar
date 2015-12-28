# Copyright (c) 2013 Red Hat, Inc.
# Copyright 2014 Catalyst IT Ltd
#
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

import sqlalchemy as sa

from zaqar.common import decorators
from zaqar import storage
from zaqar.storage.sqlalchemy import controllers
from zaqar.storage.sqlalchemy import options
from zaqar.storage.sqlalchemy import tables


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)
        self.conf.register_opts(options.MANAGEMENT_SQLALCHEMY_OPTIONS,
                                group=options.MANAGEMENT_SQLALCHEMY_GROUP)
        self.sqlalchemy_conf = self.conf[options.MANAGEMENT_SQLALCHEMY_GROUP]

    def _sqlite_on_connect(self, conn, record):
        # NOTE(flaper87): This is necessary in order
        # to ensure FK are treated correctly by sqlite.
        conn.execute('pragma foreign_keys=ON')

    def _mysql_on_connect(self, conn, record):
        # NOTE(flaper87): This is necessary in order
        # to ensure that all date operations in mysql
        # happen in UTC, `now()` for example.
        conn.query('SET time_zone = "+0:00"')

    @decorators.lazy_property(write=False)
    def engine(self, *args, **kwargs):
        uri = self.sqlalchemy_conf.uri
        engine = sa.create_engine(uri, **kwargs)

        # TODO(flaper87): Find a better way
        # to do this.
        if uri.startswith('sqlite://'):
            sa.event.listen(engine, 'connect',
                            self._sqlite_on_connect)

        if (uri.startswith('mysql://') or
                uri.startswith('mysql+pymysql://')):
            sa.event.listen(engine, 'connect',
                            self._mysql_on_connect)

        tables.metadata.create_all(engine, checkfirst=True)
        return engine

    # TODO(cpp-cabrera): expose connect/close as a context manager
    # that acquires the connection to the DB for the desired scope and
    # closes it once the operations are completed
    @decorators.lazy_property(write=False)
    def connection(self):
        return self.engine.connect()

    def run(self, *args, **kwargs):
        return self.connection.execute(*args, **kwargs)

    def close(self):
        self.connection.close()

    @property
    def pools_controller(self):
        return controllers.PoolsController(self)

    @property
    def queue_controller(self):
        return controllers.QueueController(self)

    @property
    def catalogue_controller(self):
        return controllers.CatalogueController(self)

    @property
    def flavors_controller(self):
        return controllers.FlavorsController(self)

    @property
    def subscriptions_controller(self):
        pass

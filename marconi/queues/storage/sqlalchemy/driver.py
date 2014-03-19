# Copyright (c) 2013 Red Hat, Inc.
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

import contextlib

import sqlalchemy as sa

from marconi.common import decorators
from marconi.queues import storage
from marconi.queues.storage.sqlalchemy import controllers
from marconi.queues.storage.sqlalchemy import options
from marconi.queues.storage.sqlalchemy import tables
from marconi.queues.storage.sqlalchemy import utils


class DataDriver(storage.DataDriverBase):

    def __init__(self, conf, cache):
        super(DataDriver, self).__init__(conf, cache)

        opts = options.SQLALCHEMY_OPTIONS
        self.conf.register_opts(opts,
                                group=options.SQLALCHEMY_GROUP)
        self.sqlalchemy_conf = self.conf[options.SQLALCHEMY_GROUP]

    def _sqlite_on_connect(self, conn, record):
        # NOTE(flaper87): This is necesary in order
        # to ensure FK are treated correctly by sqlite.
        conn.execute('pragma foreign_keys=ON')

    def _mysql_on_connect(self, conn, record):
        # NOTE(flaper87): This is necesary in order
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

        if uri.startswith('mysql://'):
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

    def close_connection(self):
        self.connection.close()

    @contextlib.contextmanager
    def trans(self):
        with self.engine.begin() as connection:
            yield connection

    def run(self, statement):
        """Performs a SQL query.

        :param sql: a query string with the '?' placeholders
        :param args: the arguments to substitute the placeholders
        """
        return self.connection.execute(statement)

    def get(self, statement):
        """Runs sql and returns the first entry in the results.

        :raises: utils.NoResult if the result set is empty
        """
        res = self.run(statement)
        r = res.fetchone()
        if r is None:
            raise utils.NoResult()
        else:
            res.close()
            return r

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        return controllers.QueueController(self)

    @decorators.lazy_property(write=False)
    def message_controller(self):
        return controllers.MessageController(self)

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        return controllers.ClaimController(self)

    def is_alive(self):
        return True


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)
        self.conf.register_opts(options.SQLALCHEMY_OPTIONS,
                                group=options.SQLALCHEMY_GROUP)
        self.sqlalchemy_conf = self.conf[options.SQLALCHEMY_GROUP]

    @decorators.lazy_property(write=False)
    def engine(self, *args, **kwargs):
        engine = sa.create_engine(self.sqlalchemy_conf.uri, **kwargs)
        tables.metadata.create_all(engine, checkfirst=True)
        return engine

    # TODO(cpp-cabrera): expose connect/close as a context manager
    # that acquires the connection to the DB for the desired scope and
    # closes it once the operations are completed
    @decorators.lazy_property(write=False)
    def connection(self):
        return self.engine.connect()

    def close_connection(self):
        self.connection.close()

    @property
    def shards_controller(self):
        return controllers.ShardsController(self)

    @property
    def catalogue_controller(self):
        return controllers.CatalogueController(self)

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

import contextlib
import logging

import sqlalchemy as sa

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar import storage
from zaqar.storage.sqlalchemy import controllers
from zaqar.storage.sqlalchemy import options
from zaqar.storage.sqlalchemy import tables
from zaqar.storage.sqlalchemy import utils


LOG = logging.getLogger(__name__)


class DataDriver(storage.DataDriverBase):

    _DRIVER_OPTIONS = options._config_options()

    def __init__(self, conf, cache):
        super(DataDriver, self).__init__(conf, cache)

        self.sqlalchemy_conf = self.conf[options.MESSAGE_SQLALCHEMY_GROUP]
        LOG.warn(_('sqlalchemy\'s data plane driver will be removed during '
                   'the next release. Please, consider moving your data to '
                   'one of the other supported drivers.'))

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

    def _health(self):
        KPI = {}
        # Leverage the is_alive to indicate if the backend storage is
        # reachable or not
        KPI['storage_reachable'] = self.is_alive()
        KPI['operation_status'] = self._get_operation_status()
        message_volume = {'free': 0, 'claimed': 0, 'total': 0}

        # NOTE(flwang): Using SQL directly to get better performance than
        # sqlalchemy.
        msg_count_claimed = self.get('SELECT COUNT(*) FROM MESSAGES'
                                     ' WHERE CID IS NOT NULL')
        message_volume['claimed'] = int(msg_count_claimed[0])

        msg_count_total = self.get('SELECT COUNT(*) FROM MESSAGES')
        message_volume['total'] = int(msg_count_total[0])

        message_volume['free'] = (message_volume['total'] -
                                  message_volume['claimed'])
        KPI['message_volume'] = message_volume
        return KPI


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)
        self.conf.register_opts(options.MANAGEMENT_SQLALCHEMY_OPTIONS,
                                group=options.MANAGEMENT_SQLALCHEMY_GROUP)
        self.sqlalchemy_conf = self.conf[options.MANAGEMENT_SQLALCHEMY_GROUP]

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
    def pools_controller(self):
        return controllers.PoolsController(self)

    @property
    def catalogue_controller(self):
        return controllers.CatalogueController(self)

    @property
    def flavors_controller(self):
        # NOTE(flaper87): Needed to avoid `abc` errors.
        pass

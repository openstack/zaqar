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

import contextlib
import sqlite3
import uuid

import msgpack
from oslo.config import cfg

from marconi.common import decorators
from marconi.queues import storage
from marconi.queues.storage.sqlite import controllers
from marconi.queues.storage.sqlite import utils


_SQLITE_OPTIONS = [
    cfg.StrOpt('database', default=':memory:',
               help='Sqlite database to use.')
]

_SQLITE_GROUP = 'drivers:storage:sqlite'


class DataDriver(storage.DataDriverBase):

    def __init__(self, conf, cache):
        super(DataDriver, self).__init__(conf, cache)

        self.conf.register_opts(_SQLITE_OPTIONS, group=_SQLITE_GROUP)
        self.sqlite_conf = self.conf[_SQLITE_GROUP]

        self.__path = self.sqlite_conf.database

    @decorators.lazy_property(write=False)
    def connection(self):
        return sqlite3.connect(self.__path,
                               detect_types=sqlite3.PARSE_DECLTYPES)

    @decorators.lazy_property(write=False)
    def database(self):
        db = self.connection.cursor()
        db.execute('''PRAGMA foreign_keys = ON''')

        self._ensure_tables(db)
        return db

    def _ensure_tables(self, db):
        """Creates tables if they don't already exist."""

        # NOTE(kgriffs): Create tables all together rather
        # than separately in each controller, since some queries
        # in the individual controllers actually require the
        # presence of more than one table.

        # NOTE(flaper87): Consider moving tables definition
        # outside this method.

        db.execute('''
            create table
            if not exists
            Messages (
                id INTEGER,
                qid INTEGER,
                ttl INTEGER,
                content DOCUMENT,
                client UUID,
                created DATETIME,  -- seconds since the Julian day
                PRIMARY KEY(id),
                FOREIGN KEY(qid) references Queues(id) on delete cascade
            )
        ''')

        db.execute('''
            create table
            if not exists
            Queues (
                id INTEGER,
                project TEXT,
                name TEXT,
                metadata DOCUMENT,
                PRIMARY KEY(id),
                UNIQUE(project, name)
            )
        ''')

        db.execute('''
            create table
            if not exists
            Claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qid INTEGER,
                ttl INTEGER,
                created DATETIME,  -- seconds since the Julian day
                FOREIGN KEY(qid) references Queues(id) on delete cascade
            )
        ''')

        db.execute('''
            create table
            if not exists
            Locked (
                cid INTEGER,
                msgid INTEGER,
                FOREIGN KEY(cid) references Claims(id) on delete cascade,
                FOREIGN KEY(msgid) references Messages(id) on delete cascade
            )
        ''')

    @staticmethod
    def pack(o):
        """Converts a Python variable to a custom SQlite `DOCUMENT`.

        :param o: a Python str, unicode, int, long, float, bool, None
                  or a dict or list of %o
        """
        return sqlite3.Binary(msgpack.dumps(o))

    sqlite3.register_converter('DOCUMENT', lambda s:
                               msgpack.loads(s, encoding='utf-8'))

    @staticmethod
    def uuid(o):
        """Converts a UUID object to a custom SQlite `UUID`.

        :param o: a UUID object
        """
        return sqlite3.Binary(o.bytes)

    sqlite3.register_converter('UUID', lambda s:
                               uuid.UUID(hex=s))

    def run(self, sql, *args):
        """Performs a SQL query.

        :param sql: a query string with the '?' placeholders
        :param args: the arguments to substitute the placeholders
        """
        return self.database.execute(sql, args)

    def run_multiple(self, sql, it):
        """Iteratively perform multiple SQL queries.

        :param sql: a query string with the '?' placeholders
        :param it: an iterator which yields a sequence of arguments to
                   substitute the placeholders
        """
        self.database.executemany(sql, it)

    def get(self, sql, *args):
        """Runs %sql and returns the first entry in the results.

        :param sql: a query string with the '?' placeholders
        :param args: the arguments to substitute the placeholders
        :raises: utils.NoResult if the result set is empty
        """
        try:
            return next(self.run(sql, *args))

        except StopIteration:
            raise utils.NoResult()

    @property
    def affected(self):
        """Checks whether a row is affected in the last operation."""
        assert self.database.rowcount in (0, 1)
        return self.database.rowcount == 1

    @property
    def lastrowid(self):
        """Returns the last inserted row id."""
        return self.database.lastrowid

    @contextlib.contextmanager
    def __call__(self, isolation):
        self.run('begin ' + isolation)
        try:
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def is_alive(self):
        return True

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        return controllers.QueueController(self)

    @decorators.lazy_property(write=False)
    def message_controller(self):
        return controllers.MessageController(self)

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        return controllers.ClaimController(self)


class ControlDriver(storage.ControlDriverBase):

    def __init__(self, conf, cache):
        super(ControlDriver, self).__init__(conf, cache)

        self.conf.register_opts(_SQLITE_OPTIONS, group=_SQLITE_GROUP)
        self.sqlite_conf = self.conf[_SQLITE_GROUP]

        self.__path = self.sqlite_conf.database

    @decorators.lazy_property(write=False)
    def connection(self):
        return sqlite3.connect(self.__path,
                               detect_types=sqlite3.PARSE_DECLTYPES)

    @decorators.lazy_property(write=False)
    def database(self):
        db = self.connection.cursor()
        db.execute('''PRAGMA foreign_keys = ON''')
        return db

    @property
    def catalogue_controller(self):
        return controllers.CatalogueController(self)

    @property
    def shards_controller(self):
        return controllers.ShardsController(self)

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

import msgpack

from marconi.common import config
from marconi import storage
from marconi.storage.sqlite import controllers

CFG = config.namespace('drivers:storage:sqlite').from_options(
    database=':memory:')


class Driver(storage.DriverBase):

    def __init__(self):
        self.__path = CFG.database
        self.__conn = sqlite3.connect(self.__path,
                                      detect_types=sqlite3.PARSE_DECLTYPES)
        self.__db = self.__conn.cursor()
        self.run('''PRAGMA foreign_keys = ON''')

    @staticmethod
    def pack(o):
        """Converts a Python variable to a custom SQlite `DOCUMENT`.

        :param o: a Python str, unicode, int, long, float, bool, None
                  or a dict or list of %o
        """
        return buffer(msgpack.dumps(o))

    sqlite3.register_converter('DOCUMENT', lambda s:
                               msgpack.loads(s, encoding='utf-8'))

    def run(self, sql, *args):
        """Performs a SQL query.

        :param sql: a query string with the '?' placeholders
        :param args: the arguments to substitute the placeholders
        """
        return self.__db.execute(sql, args)

    def run_multiple(self, sql, it):
        """Iteratively perform multiple SQL queries.

        :param sql: a query string with the '?' placeholders
        :param it: an iterator which yields a sequence of arguments to
                   substitute the placeholders
        """
        self.__db.executemany(sql, it)

    def get(self, sql, *args):
        """Runs %sql and returns the first entry in the results.

        :param sql: a query string with the '?' placeholders
        :param args: the arguments to substitute the placeholders
        :raises: _NoResult if the result set is empty
        """
        try:
            return self.run(sql, *args).next()

        except StopIteration:
            raise controllers._NoResult

    @property
    def affected(self):
        """Checks whether a row is affected in the last operation."""
        assert self.__db.rowcount in (0, 1)
        return self.__db.rowcount == 1

    @property
    def lastrowid(self):
        """Returns the last inserted row id."""
        return self.__db.lastrowid

    @contextlib.contextmanager
    def __call__(self, isolation):
        self.run('begin ' + isolation)
        try:
            yield
            self.__conn.commit()
        except Exception:
            self.__conn.rollback()
            raise

    @property
    def queue_controller(self):
        return controllers.Queue(self)

    @property
    def message_controller(self):
        return controllers.Message(self)

    @property
    def claim_controller(self):
        return controllers.Claim(self)

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


import sqlite3

from marconi.common import config
from marconi import storage
from marconi.storage.sqlite import controllers


cfg = config.namespace('drivers:storage:sqlite').from_options(
    database=':memory:')


class Driver(storage.DriverBase):
    def __init__(self):
        self.__path = cfg.database
        self.__conn = sqlite3.connect(self.__path)
        self.__db = self.__conn.cursor()
        self._run('''PRAGMA foreign_keys = ON''')

    def _run(self, sql, *args):
        return self.__db.execute(sql, args)

    def _run_multiple(self, sql, it):
        self.__db.executemany(sql, it)

    def _get(self, sql, *args):
        return self._run(sql, *args).fetchone()

    def __enter__(self):
        self._run('begin immediate')

    def __exit__(self, exc_type, exc_value, traceback):
        self.__conn.commit()

    @property
    def queue_controller(self):
        return controllers.Queue(self)

    @property
    def message_controller(self):
        return controllers.Message(self)

    @property
    def claim_controller(self):
        return None

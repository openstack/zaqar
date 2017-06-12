# Copyright (c) 2014 Rackspace Hosting, Inc.
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

"""Sql storage controller for the queues catalogue.

Serves to construct an association between a project + queue -> pool

name: string -> Pools.name
project: string
queue: string
"""

import oslo_db.exception
import sqlalchemy as sa

from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.sqlalchemy import tables


def _match(project, queue):
    clauses = [
        tables.Catalogue.c.project == project,
        tables.Catalogue.c.queue == queue
    ]
    return sa.sql.and_(*clauses)


class CatalogueController(base.CatalogueBase):

    def list(self, project):
        stmt = sa.sql.select([tables.Catalogue]).where(
            tables.Catalogue.c.project == project
        )
        cursor = self.driver.run(stmt)
        return (_normalize(v) for v in cursor)

    def get(self, project, queue):
        stmt = sa.sql.select([tables.Catalogue]).where(
            _match(project, queue)
        )
        entry = self.driver.run(stmt).fetchone()

        if entry is None:
            raise errors.QueueNotMapped(queue, project)

        return _normalize(entry)

    def exists(self, project, queue):
        try:
            return self.get(project, queue) is not None
        except errors.QueueNotMapped:
            return False

    def insert(self, project, queue, pool):
        try:
            stmt = sa.sql.insert(tables.Catalogue).values(
                project=project, queue=queue, pool=pool
            )
            self.driver.run(stmt)

        except oslo_db.exception.DBReferenceError:
            self._update(project, queue, pool)
        except oslo_db.exception.DBDuplicateError:
            self._update(project, queue, pool)

    def delete(self, project, queue):
        stmt = sa.sql.delete(tables.Catalogue).where(
            _match(project, queue)
        )
        self.driver.run(stmt)

    def _update(self, project, queue, pool):
        stmt = sa.sql.update(tables.Catalogue).where(
            _match(project, queue)
        ).values(pool=pool)
        self.driver.run(stmt)

    def update(self, project, queue, pool=None):
        if pool is None:
            return

        if not self.exists(project, queue):
            raise errors.QueueNotMapped(queue, project)

        self._update(project, queue, pool)

    def drop_all(self):
        stmt = sa.sql.expression.delete(tables.Catalogue)
        self.driver.run(stmt)


def _normalize(entry):
    name, project, queue = entry
    return {
        'queue': queue,
        'project': project,
        'pool': name
    }

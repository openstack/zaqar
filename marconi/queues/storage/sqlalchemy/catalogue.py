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

Serves to construct an association between a project + queue -> shard

name: string -> Shards.name
project: string
queue: string
"""

import sqlalchemy as sa

from marconi.queues.storage import base
from marconi.queues.storage import errors
from marconi.queues.storage.sqlalchemy import tables


def _match(project, queue):
    clauses = [
        tables.Catalogue.c.project == project,
        tables.Catalogue.c.queue == queue
    ]
    return sa.sql.and_(*clauses)


class CatalogueController(base.CatalogueBase):

    def __init__(self, *args, **kwargs):
        super(CatalogueController, self).__init__(*args, **kwargs)

        self._conn = self.driver.connection

    def list(self, project):
        stmt = sa.sql.select([tables.Catalogue]).where(
            tables.Catalogue.c.project == project
        )
        cursor = self._conn.execute(stmt)
        return (_normalize(v) for v in cursor)

    def get(self, project, queue):
        stmt = sa.sql.select([tables.Catalogue]).where(
            _match(project, queue)
        )
        entry = self._conn.execute(stmt).fetchone()

        if entry is None:
            raise errors.QueueNotMapped(project, queue)

        return _normalize(entry)

    def exists(self, project, queue):
        try:
            return self.get(project, queue) is not None
        except errors.QueueNotMapped:
            return False

    def insert(self, project, queue, shard):
        try:
            stmt = sa.sql.insert(tables.Catalogue).values(
                project=project, queue=queue, shard=shard
            )
            self._conn.execute(stmt)

        except sa.exc.IntegrityError:
            self.update(project, queue, shard)

    def delete(self, project, queue):
        stmt = sa.sql.delete(tables.Catalogue).where(
            _match(project, queue)
        )
        self._conn.execute(stmt)

    def update(self, project, queue, shard=None):
        if shard is None:
            return

        if not self.exists(project, queue):
            raise errors.QueueNotMapped(project, queue)

        stmt = sa.sql.update(tables.Catalogue).where(
            _match(project, queue)
        ).values(shard=shard)
        self._conn.execute(stmt)

    def drop_all(self):
        stmt = sa.sql.expression.delete(tables.Catalogue)
        self._conn.execute(stmt)


def _normalize(entry):
    name, project, queue = entry
    return {
        'queue': queue,
        'project': project,
        'shard': name
    }

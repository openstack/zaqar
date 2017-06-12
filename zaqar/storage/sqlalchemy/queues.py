# Copyright (c) 2014 Red Hat, Inc.
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

import oslo_db.exception
import sqlalchemy as sa

from zaqar import storage
from zaqar.storage import errors
from zaqar.storage.sqlalchemy import tables
from zaqar.storage.sqlalchemy import utils


class QueueController(storage.Queue):

    def _list(self, project, marker=None,
              limit=storage.DEFAULT_QUEUES_PER_PAGE, detailed=False):

        if project is None:
            project = ''

        fields = [tables.Queues.c.name]
        if detailed:
            fields.append(tables.Queues.c.metadata)

        if marker:
            sel = sa.sql.select(fields, sa.and_(
                                tables.Queues.c.project == project,
                                tables.Queues.c.name > marker))
        else:
            sel = sa.sql.select(fields, tables.Queues.c.project == project)

        sel = sel.order_by(sa.asc(tables.Queues.c.name)).limit(limit)
        records = self.driver.run(sel)

        marker_name = {}

        def it():
            for rec in records:
                marker_name['next'] = rec[0]
                yield ({'name': rec[0]} if not detailed
                       else
                       {'name': rec[0], 'metadata': utils.json_decode(rec[1])})

        yield it()
        yield marker_name and marker_name['next']

    def get_metadata(self, name, project):
        if project is None:
            project = ''

        sel = sa.sql.select([tables.Queues.c.metadata], sa.and_(
            tables.Queues.c.project == project,
            tables.Queues.c.name == name
        ))

        queue = self.driver.run(sel).fetchone()
        if queue is None:
            raise errors.QueueDoesNotExist(name, project)

        return utils.json_decode(queue[0])

    def _get(self, name, project=None):
        try:
            return self.get_metadata(name, project)
        except errors.QueueDoesNotExist:
            return {}

    def _create(self, name, metadata=None, project=None):
        if project is None:
            project = ''

        try:
            smeta = utils.json_encode(metadata or {})
            ins = tables.Queues.insert().values(project=project,
                                                name=name,
                                                metadata=smeta)
            res = self.driver.run(ins)
        except oslo_db.exception.DBDuplicateEntry:
            return False

        return res.rowcount == 1

    def _exists(self, name, project):
        if project is None:
            project = ''

        sel = sa.sql.select([tables.Queues.c.id], sa.and_(
                            tables.Queues.c.project == project,
                            tables.Queues.c.name == name
                            ))
        res = self.driver.run(sel)
        r = res.fetchone()
        res.close()
        return r is not None

    def set_metadata(self, name, metadata, project):
        if project is None:
            project = ''

        update = (tables.Queues.update().
                  where(sa.and_(
                      tables.Queues.c.project == project,
                      tables.Queues.c.name == name)).
                  values(metadata=utils.json_encode(metadata)))

        res = self.driver.run(update)

        try:
            if res.rowcount != 1:
                raise errors.QueueDoesNotExist(name, project)
        finally:
            res.close()

    def _delete(self, name, project):
        if project is None:
            project = ''

        dlt = tables.Queues.delete().where(sa.and_(
            tables.Queues.c.project == project,
            tables.Queues.c.name == name))
        self.driver.run(dlt)

    def _stats(self, name, project):
        pass

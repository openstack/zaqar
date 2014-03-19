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

import json

import sqlalchemy as sa
from sqlalchemy.sql import func as sfunc

from marconi.queues import storage
from marconi.queues.storage import errors
from marconi.queues.storage.sqlalchemy import tables
from marconi.queues.storage.sqlalchemy import utils


class QueueController(storage.Queue):

    def list(self, project, marker=None,
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
                       {'name': rec[0], 'metadata': json.loads(rec[1])})

        yield it()
        yield marker_name['next']

    def get_metadata(self, name, project):
        if project is None:
            project = ''

        try:
            sel = sa.sql.select([tables.Queues.c.metadata], sa.and_(
                                tables.Queues.c.project == project,
                                tables.Queues.c.name == name
                                ))
            return json.loads(self.driver.get(sel)[0])
        except utils.NoResult:
            raise errors.QueueDoesNotExist(name, project)

    def create(self, name, project):
        if project is None:
            project = ''

        try:
            ins = tables.Queues.insert().values(project=project, name=name,
                                                metadata=json.dumps({}))
            res = self.driver.run(ins)
        except sa.exc.IntegrityError:
            return False

        return res.rowcount == 1

    def exists(self, name, project):
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

        update = tables.Queues.update().\
            where(sa.and_(
                tables.Queues.c.project == project,
                tables.Queues.c.name == name)).\
            values(metadata=json.dumps(metadata))
        res = self.driver.run(update)

        try:
            if res.rowcount != 1:
                raise errors.QueueDoesNotExist(name, project)
        finally:
            res.close()

    def delete(self, name, project):
        if project is None:
            project = ''

        dlt = tables.Queues.delete().where(sa.and_(
            tables.Queues.c.project == project,
            tables.Queues.c.name == name))
        self.driver.run(dlt)

    def stats(self, name, project):
        if project is None:
            project = ''

        qid = utils.get_qid(self.driver, name, project)
        sel = sa.sql.select([
            sa.sql.select([sa.func.count(tables.Messages.c.id)],
                          sa.and_(
                              tables.Messages.c.qid == qid,
                              tables.Messages.c.cid != (None),
                              tables.Messages.c.ttl >
                              sfunc.now() - tables.Messages.c.created,
                          )),
            sa.sql.select([sa.func.count(tables.Messages.c.id)],
                          sa.and_(
                              tables.Messages.c.qid == qid,
                              tables.Messages.c.cid == (None),
                              tables.Messages.c.ttl >
                              sfunc.now() - tables.Messages.c.created,
                          ))
        ])

        claimed, free = self.driver.get(sel)

        total = free + claimed

        message_stats = {
            'claimed': claimed,
            'free': free,
            'total': total,
        }

        try:
            message_controller = self.driver.message_controller
            oldest = message_controller.first(name, project, sort=1)
            newest = message_controller.first(name, project, sort=-1)
        except errors.QueueIsEmpty:
            pass
        else:
            message_stats['oldest'] = utils.stat_message(oldest)
            message_stats['newest'] = utils.stat_message(newest)

        return {'messages': message_stats}

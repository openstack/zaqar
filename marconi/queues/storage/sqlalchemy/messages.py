# Copyright (c) 2014 Red Hat, Inc.
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

import calendar
import json

import sqlalchemy as sa
from sqlalchemy.sql import func as sfunc

from marconi.openstack.common import timeutils
from marconi.queues import storage
from marconi.queues.storage import errors
from marconi.queues.storage.sqlalchemy import tables
from marconi.queues.storage.sqlalchemy import utils


class MessageController(storage.Message):

    def _get(self, queue, message_id, project, count=False):

        if project is None:
            project = ''

        mid = utils.msgid_decode(message_id)

        if mid is None:
            raise errors.MessageDoesNotExist(message_id, queue, project)

        try:
            j = sa.join(tables.Messages, tables.Queues,
                        tables.Messages.c.qid == tables.Queues.c.id)

            sel = sa.sql.select([tables.Messages.c.body,
                                 tables.Messages.c.ttl,
                                 tables.Messages.c.created])

            if count:
                sel = sa.sql.select([sfunc.count(tables.Messages.c.id)])

            sel = sel.select_from(j)
            sel = sel.where(sa.and_(tables.Messages.c.id == mid,
                                    tables.Queues.c.project == project,
                                    tables.Queues.c.name == queue,
                                    tables.Messages.c.ttl >
                                    sfunc.now() - tables.Messages.c.created))

            return self.driver.get(sel)
        except utils.NoResult:
            raise errors.MessageDoesNotExist(message_id, queue, project)

    def _exists(self, queue, message_id, project):
        try:
            # NOTE(flaper87): Use count to avoid returning
            # unnecessary data from the database.
            self._get(queue, message_id, project, count=True)
            return True
        except errors.MessageDoesNotExist:
            return False

    def get(self, queue, message_id, project):
        body, ttl, created = self._get(queue, message_id, project)
        now = timeutils.utcnow_ts()
        return {
            'id': message_id,
            'ttl': ttl,
            'age': now - calendar.timegm(created.timetuple()),
            'body': json.loads(body),
        }

    def bulk_get(self, queue, message_ids, project):
        if project is None:
            project = ''

        message_ids = [id for id in
                       map(utils.msgid_decode, message_ids)
                       if id is not None]

        statement = sa.sql.select([tables.Messages.c.id,
                                   tables.Messages.c.body,
                                   tables.Messages.c.ttl,
                                   tables.Messages.c.created])

        and_stmt = [tables.Messages.c.id.in_(message_ids),
                    tables.Queues.c.name == queue,
                    tables.Queues.c.project == project,
                    tables.Messages.c.ttl >
                    sfunc.now() - tables.Messages.c.created]

        j = sa.join(tables.Messages, tables.Queues,
                    tables.Messages.c.qid == tables.Queues.c.id)

        statement = statement.select_from(j).where(sa.and_(*and_stmt))

        now = timeutils.utcnow_ts()
        records = self.driver.run(statement)
        for id, body, ttl, created in records:
            yield {
                'id': utils.msgid_encode(int(id)),
                'ttl': ttl,
                'age': now - calendar.timegm(created.timetuple()),
                'body': json.loads(body),
            }

    def first(self, queue, project=None, sort=1):
        if project is None:
            project = ''

        qid = utils.get_qid(self.driver, queue, project)

        sel = sa.sql.select([tables.Messages.c.id,
                             tables.Messages.c.body,
                             tables.Messages.c.ttl,
                             tables.Messages.c.created],
                            sa.and_(
                                tables.Messages.c.ttl >
                                sfunc.now() - tables.Messages.c.created,
                                tables.Messages.c.qid == qid))
        if sort not in (1, -1):
            raise ValueError(u'sort must be either 1 (ascending) '
                             u'or -1 (descending)')

        order = sa.asc
        if sort == -1:
            order = sa.desc

        sel = sel.order_by(order(tables.Messages.c.id))

        try:
            id, body, ttl, created = self.driver.get(sel)
        except utils.NoResult:
            raise errors.QueueIsEmpty(queue, project)

        created_iso = timeutils.isotime(created)
        return {
            'id': utils.msgid_encode(int(id)),
            'ttl': ttl,
            'created': created_iso,
            'age': int((timeutils.utcnow() - created).seconds),
            'body': body,
        }

    def list(self, queue, project, marker=None,
             limit=storage.DEFAULT_MESSAGES_PER_PAGE,
             echo=False, client_uuid=None, include_claimed=False):

        if project is None:
            project = ''

        with self.driver.trans() as trans:
            sel = sa.sql.select([tables.Messages.c.id,
                                 tables.Messages.c.body,
                                 tables.Messages.c.ttl,
                                 tables.Messages.c.created])

            j = sa.join(tables.Messages, tables.Queues,
                        tables.Messages.c.qid == tables.Queues.c.id)

            sel = sel.select_from(j)
            and_clause = [tables.Queues.c.name == queue,
                          tables.Queues.c.project == project]

            if not echo:
                and_clause.append(tables.Messages.c.client != str(client_uuid))

            if marker:
                mark = utils.marker_decode(marker)
                if mark:
                    and_clause.append(tables.Messages.c.id > mark)
                else:
                    # NOTE(flaper87): Awful hack.
                    # If the marker is invalid, we don't want to
                    # return *any* record. Since rows PKs start
                    # from 0, it won't match anything and the query
                    # will still be fast.
                    and_clause.append(tables.Messages.c.id < -1)

            if not include_claimed:
                and_clause.append(tables.Messages.c.cid == (None))

            sel = sel.where(sa.and_(*and_clause))
            sel = sel.limit(limit)

            records = trans.execute(sel)
            marker_id = {}

            def it():
                now = timeutils.utcnow_ts()
                for id, body, ttl, created in records:
                    marker_id['next'] = id
                    yield {
                        'id': utils.msgid_encode(id),
                        'ttl': ttl,
                        'age': now - calendar.timegm(created.timetuple()),
                        'body': json.loads(body),
                    }

            yield it()
            yield utils.marker_encode(marker_id['next'])

    def post(self, queue, messages, client_uuid, project):
        if project is None:
            project = ''

        with self.driver.trans() as trans:
            qid = utils.get_qid(self.driver, queue, project)

            # cleanup all expired messages in this queue
            #self.driver.run('''
            #    delete from Messages
            #     where ttl <= julianday() * 86400.0 - created
            #       and qid = ?''', qid)

            # executemany() sets lastrowid to None, so no matter we manually
            # generate the IDs or not, we still need to query for it.

            def it():
                for m in messages:
                    yield dict(qid=qid,
                               ttl=m['ttl'],
                               body=json.dumps(m['body']),
                               client=str(client_uuid))

            result = trans.execute(tables.Messages.insert(), list(it()))

            statement = sa.sql.select([tables.Messages.c.id])
            statement = statement.limit(result.rowcount)
            statement = statement.order_by(tables.Messages.c.id.desc())
            result = trans.execute(statement).fetchall()

        return map(utils.msgid_encode, [i[0] for i in reversed(result)])

    def delete(self, queue, message_id, project, claim=None):
        if project is None:
            project = ''

        mid = utils.msgid_decode(message_id)
        if mid is None:
            return

        with self.driver.trans() as trans:
            if not self._exists(queue, message_id, project):
                return

            statement = tables.Messages.delete()
            and_stmt = [tables.Messages.c.id == mid]

            exists = sa.sql.select([tables.Messages.c.id], sa.and_(*and_stmt))

            if not trans.execute(exists).first():
                return

            cid = claim and utils.cid_decode(claim) or None

            if claim and cid is None:
                return

            and_stmt.append(tables.Messages.c.cid == cid)

            statement = statement.where(sa.and_(*and_stmt))
            res = trans.execute(statement)

            if res.rowcount == 0:
                raise errors.MessageIsClaimed(mid)

    def bulk_delete(self, queue, message_ids, project):
        if project is None:
            project = ''

        message_ids = [id for id in
                       map(utils.msgid_decode, message_ids) if id]

        with self.driver.trans() as trans:
            try:
                qid = utils.get_qid(self.driver, queue, project)
            except errors.QueueDoesNotExist:
                return

            statement = tables.Messages.delete()

            and_stmt = [tables.Messages.c.id.in_(message_ids),
                        tables.Messages.c.qid == qid]

            trans.execute(statement.where(sa.and_(*and_stmt)))

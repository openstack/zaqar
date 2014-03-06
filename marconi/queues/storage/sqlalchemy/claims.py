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

import sqlalchemy as sa
from sqlalchemy.sql import func as sfunc

from marconi.openstack.common import timeutils
from marconi.queues import storage
from marconi.queues.storage import errors
from marconi.queues.storage.sqlalchemy import tables
from marconi.queues.storage.sqlalchemy import utils


class ClaimController(storage.Claim):

    def __get(self, cid, trans):
        # NOTE(flaper87): This probably needs to
        # join on `Claim` to check the claim ttl.
        sel = sa.sql.select([tables.Messages.c.id,
                             tables.Messages.c.body,
                             tables.Messages.c.ttl,
                             tables.Messages.c.created],
                            sa.and_(
                                tables.Messages.c.ttl >
                                utils.get_age(tables.Messages.c.created),
                                #tables.Messages.c.ttl >
                                #utils.get_age(tables.Claims.c.created),
                                tables.Messages.c.cid == cid
                            ))
        records = trans.execute(sel)

        for id, body, ttl, created in records:
            yield {
                'id': utils.msgid_encode(int(id)),
                'ttl': ttl,
                'age': (timeutils.utcnow() - created).seconds,
                'body': body,
            }

    def get(self, queue, claim_id, project=None):
        if project is None:
            project = ''

        cid = utils.cid_decode(claim_id)
        if cid is None:
            raise errors.ClaimDoesNotExist(claim_id, queue, project)

        with self.driver.trans() as trans:
            sel = sa.sql.select([tables.Claims.c.id,
                                 tables.Claims.c.ttl,
                                 tables.Claims.c.created],
                                sa.and_(tables.Claims.c.ttl >
                                        utils.get_age(tables.Claims.c.created),
                                        tables.Claims.c.id == cid,
                                        tables.Queues.c.project == project,
                                        tables.Queues.c.name == queue),
                                from_obj=[tables.Queues.join(tables.Claims)])

            res = trans.execute(sel).fetchone()
            if res is None:
                raise errors.ClaimDoesNotExist(claim_id, queue, project)

            cid, ttl, created = res
            return (
                {'id': claim_id,
                 'ttl': ttl,
                 'age': (timeutils.utcnow() - created).seconds},
                list(self.__get(cid, trans))
            )

    def create(self, queue, metadata, project=None,
               limit=storage.DEFAULT_MESSAGES_PER_CLAIM):

        if project is None:
            project = ''

        with self.driver.trans() as trans:
            try:
                qid = utils.get_qid(self.driver, queue, project)
            except errors.QueueDoesNotExist:
                return None, iter([])

            # Clean up all expired claims in this queue
            dlt = tables.Claims.delete().where(sa.and_(
                tables.Claims.c.ttl <=
                utils.get_age(tables.Claims.c.created),
                tables.Claims.c.qid == qid))
            trans.execute(dlt)

            ins = tables.Claims.insert().values(qid=qid, ttl=metadata['ttl'])
            res = trans.execute(ins)

            cid = res.lastrowid

            and_stmt = sa.and_(tables.Messages.c.cid == (None),
                               tables.Messages.c.ttl >
                               sfunc.now() - tables.Messages.c.created,
                               tables.Messages.c.qid == qid)
            sel = sa.sql.select([tables.Messages.c.id], and_stmt).limit(limit)

            records = [t[0] for t in trans.execute(sel)]
            and_stmt = sa.and_(tables.Messages.c.id.in_(records))
            update = tables.Messages.update().values(cid=cid).where(and_stmt)
            trans.execute(update)

            # NOTE(flaper87): I bet there's a better way
            # to do this.
            messages_ttl = metadata['ttl'] + metadata['grace']
            update = (tables.Messages.update().values(ttl=messages_ttl).
                      where(sa.and_(
                          tables.Messages.c.ttl < messages_ttl,
                          tables.Messages.c.cid == cid)))
            trans.execute(update)

            return (utils.cid_encode(int(cid)), list(self.__get(cid, trans)))

    def update(self, queue, claim_id, metadata, project=None):
        if project is None:
            project = ''

        cid = utils.cid_decode(claim_id)
        if cid is None:
            raise errors.ClaimDoesNotExist(claim_id, queue, project)

        age = utils.get_age(tables.Claims.c.created)
        with self.driver.trans() as trans:
            qid = utils.get_qid(self.driver, queue, project)

            update = tables.Claims.update().where(sa.and_(
                tables.Claims.c.ttl > age,
                tables.Claims.c.id == cid,
                tables.Claims.c.id == qid)).\
                values(ttl=metadata['ttl'])

            res = trans.execute(update)
            if res.rowcount != 1:
                raise errors.ClaimDoesNotExist(claim_id, queue, project)

            update = (tables.Messages.update().
                      values(ttl=metadata['ttl']).
                      where(sa.and_(
                          tables.Messages.c.ttl < metadata['ttl'],
                          tables.Messages.c.cid == cid)))
            trans.execute(update)

    def delete(self, queue, claim_id, project=None):
        if project is None:
            project = ''

        cid = utils.cid_decode(claim_id)
        if cid is None:
            return

        with self.driver.trans() as trans:
            try:
                # NOTE(flaper87): This could probably use some
                # joins and be just 1 query.
                qid = utils.get_qid(self.driver, queue, project)
            except errors.QueueDoesNotExist:
                return

            and_stmt = sa.and_(tables.Claims.c.id == cid,
                               tables.Claims.c.qid == qid)
            dlt = tables.Claims.delete().where(and_stmt)
            trans.execute(dlt)

            update = (tables.Messages.update().values(cid=None).
                      where(tables.Messages.c.cid == cid))

            trans.execute(update)

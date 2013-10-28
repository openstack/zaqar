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

from marconi.openstack.common import timeutils
from marconi.queues.storage import base
from marconi.queues.storage import errors
from marconi.queues.storage.sqlite import utils


class MessageController(base.MessageBase):

    def get(self, queue, message_id, project):
        if project is None:
            project = ''

        mid = utils.msgid_decode(message_id)
        if mid is None:
            raise errors.MessageDoesNotExist(message_id, queue, project)

        try:
            content, ttl, age = self.driver.get('''
                select content, ttl, julianday() * 86400.0 - created
                  from Queues as Q join Messages as M
                    on qid = Q.id
                 where ttl > julianday() * 86400.0 - created
                   and M.id = ? and project = ? and name = ?
                ''', mid, project, queue)

        except utils.NoResult:
            raise errors.MessageDoesNotExist(message_id, queue, project)

        return {
            'id': message_id,
            'ttl': ttl,
            'age': int(age),
            'body': content,
        }

    def bulk_get(self, queue, message_ids, project):
        if project is None:
            project = ''

        message_ids = ','.join(
            ["'%s'" % id for id in
             map(utils.msgid_decode, message_ids) if id is not None]
        )

        sql = '''
            select M.id, content, ttl, julianday() * 86400.0 - created
              from Queues as Q join Messages as M
                on qid = Q.id
             where ttl > julianday() * 86400.0 - created
               and M.id in (%s) and project = ? and name = ?
        ''' % message_ids

        records = self.driver.run(sql, project, queue)
        for id, content, ttl, age in records:
            yield {
                'id': utils.msgid_encode(id),
                'ttl': ttl,
                'age': int(age),
                'body': content,
            }

    def first(self, queue, project=None, sort=1):
        if project is None:
            project = ''

        with self.driver('deferred'):
            sql = '''
                select id, content, ttl, created,
                       julianday() * 86400.0 - created
                  from Messages
                 where ttl > julianday() * 86400.0 - created
                   and qid = ?
              order by id %s
                 limit 1'''

            if sort not in (1, -1):
                raise ValueError(u'sort must be either 1 (ascending) '
                                 u'or -1 (descending)')

            sql = sql % ('DESC' if sort == -1 else 'ASC')

            args = [utils.get_qid(self.driver, queue, project)]

            records = self.driver.run(sql, *args)

            try:
                id, content, ttl, created, age = next(records)
            except StopIteration:
                raise errors.QueueIsEmpty(queue, project)

            created_unix = utils.julian_to_unix(created)
            created_iso8601 = timeutils.iso8601_from_timestamp(created_unix)

            return {
                'id': utils.msgid_encode(id),
                'ttl': ttl,
                'created': created_iso8601,
                'age': age,
                'body': content,
            }

    def list(self, queue, project, marker=None, limit=None,
             echo=False, client_uuid=None, include_claimed=False):

        if limit is None:
            limit = self.driver.limits_conf.default_message_paging

        if project is None:
            project = ''

        with self.driver('deferred'):
            sql = '''
                select M.id, content, ttl, julianday() * 86400.0 - created
                  from Queues as Q join Messages as M
                    on M.qid = Q.id
                 where M.ttl > julianday() * 86400.0 - created
                   and Q.name = ? and Q.project = ?'''

            args = [queue, project]

            if not echo:
                sql += '''
                   and M.client != ?'''
                args += [self.driver.uuid(client_uuid)]

            if marker:
                sql += '''
                   and M.id > ?'''
                args += [utils.marker_decode(marker)]

            if not include_claimed:
                sql += '''
                   and M.id not in (select msgid
                                      from Claims join Locked
                                        on id = cid)'''

            sql += '''
                 limit ?'''
            args += [limit]

            records = self.driver.run(sql, *args)
            marker_id = {}

            def it():
                for id, content, ttl, age in records:
                    marker_id['next'] = id
                    yield {
                        'id': utils.msgid_encode(id),
                        'ttl': ttl,
                        'age': int(age),
                        'body': content,
                    }

            yield it()
            yield utils.marker_encode(marker_id['next'])

    def post(self, queue, messages, client_uuid, project):
        if project is None:
            project = ''

        with self.driver('immediate'):
            qid = utils.get_qid(self.driver, queue, project)

            # cleanup all expired messages in this queue

            self.driver.run('''
                delete from Messages
                 where ttl <= julianday() * 86400.0 - created
                   and qid = ?''', qid)

            # executemany() sets lastrowid to None, so no matter we manually
            # generate the IDs or not, we still need to query for it.

            unused = self.driver.get('''
                select max(id) + 1 from Messages''')[0] or 1001
            my = dict(newid=unused)

            def it():
                for m in messages:
                    yield (my['newid'], qid, m['ttl'],
                           self.driver.pack(m['body']),
                           self.driver.uuid(client_uuid))
                    my['newid'] += 1

            self.driver.run_multiple('''
                insert into Messages
                values (?, ?, ?, ?, ?, julianday() * 86400.0)''', it())

        return map(utils.msgid_encode, range(unused, my['newid']))

    def delete(self, queue, message_id, project, claim=None):
        if project is None:
            project = ''

        id = utils.msgid_decode(message_id)
        if id is None:
            return

        with self.driver('immediate'):
            message_exists, = self.driver.get('''
                select count(M.id)
                  from Queues as Q join Messages as M
                    on qid = Q.id
                 where ttl > julianday() * 86400.0 - created
                   and M.id = ? and project = ? and name = ?
            ''', id, project, queue)

            if not message_exists:
                return

            if claim is None:
                self.__delete_unclaimed(id)
            else:
                self.__delete_claimed(id, claim)

    def __delete_unclaimed(self, id):
        self.driver.run('''
            delete from Messages
             where id = ?
               and not exists (select *
                                 from Claims join Locked
                                   on id = cid
                                where ttl > julianday() * 86400.0 - created)
        ''', id)

        if not self.driver.affected:
            raise errors.MessageIsClaimed(id)

    def __delete_claimed(self, id, claim):
        # Precondition: id exists in a specific queue
        cid = utils.cid_decode(claim)
        if cid is None:
            return

        self.driver.run('''
            delete from Messages
             where id = ?
               and id in (select msgid
                            from Claims join Locked
                              on id = cid
                           where ttl > julianday() * 86400.0 - created
                             and id = ?)
        ''', id, cid)

        if not self.driver.affected:
            raise errors.MessageIsClaimedBy(id, claim)

    def bulk_delete(self, queue, message_ids, project):
        if project is None:
            project = ''

        message_ids = ','.join(
            ["'%s'" % id for id in
             map(utils.msgid_decode, message_ids) if id]
        )

        self.driver.run('''
            delete from Messages
             where id in (%s)
               and qid = (select id from Queues
                           where project = ? and name = ?)
        ''' % message_ids, project, queue)

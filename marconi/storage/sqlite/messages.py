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


import six

from marconi.storage import base
from marconi.storage import exceptions
from marconi.storage.sqlite import utils


class MessageController(base.MessageBase):
    def __init__(self, driver):
        self.driver = driver
        self.driver.run('''
            create table
            if not exists
            Messages (
                id INTEGER,
                qid INTEGER,
                ttl INTEGER,
                content DOCUMENT,
                client TEXT,
                created DATETIME,  -- seconds since the Julian day
                PRIMARY KEY(id),
                FOREIGN KEY(qid) references Queues(id) on delete cascade
            )
        ''')

    def get(self, queue, message_ids, project):
        if project is None:
            project = ''

        if isinstance(message_ids, six.string_types):
            message_ids = [message_ids]

        message_ids = ["'%s'" % utils.msgid_decode(id) for id in message_ids]
        message_ids = ','.join(message_ids)

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

    def list(self, queue, project, marker=None,
             limit=10, echo=False, client_uuid=None):

        if project is None:
            project = ''

        with self.driver('deferred'):
            sql = '''
                select id, content, ttl, julianday() * 86400.0 - created
                  from Messages
                 where ttl > julianday() * 86400.0 - created
                   and qid = ?'''
            args = [utils.get_qid(self.driver, queue, project)]

            if not echo:
                sql += '''
                   and client != ?'''
                args += [client_uuid]

            if marker:
                sql += '''
                   and id > ?'''
                args += [utils.marker_decode(marker)]

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
                           self.driver.pack(m['body']), client_uuid)
                    my['newid'] += 1

            self.driver.run_multiple('''
                insert into Messages
                values (?, ?, ?, ?, ?, julianday() * 86400.0)''', it())

        return map(utils.msgid_encode, range(unused, my['newid']))

    def delete(self, queue, message_id, project, claim=None):
        if project is None:
            project = ''

        id = utils.msgid_decode(message_id)

        if not claim:
            self.driver.run('''
                delete from Messages
                 where id = ?
                   and qid = (select id from Queues
                               where project = ? and name = ?)
            ''', id, project, queue)
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

            self.__delete_claimed(id, claim)

    def __delete_claimed(self, id, claim):
        # Precondition: id exists in a specific queue
        self.driver.run('''
            delete from Messages
             where id = ?
               and id in (select msgid
                            from Claims join Locked
                              on id = cid
                           where ttl > julianday() * 86400.0 - created
                             and id = ?)
        ''', id, utils.cid_decode(claim))

        if not self.driver.affected:
            raise exceptions.ClaimNotPermitted(utils.msgid_encode(id), claim)

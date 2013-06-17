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


from marconi.storage import base
from marconi.storage import exceptions


class Queue(base.QueueBase):
    def __init__(self, driver):
        self.driver = driver
        self.driver.run('''
            create table
            if not exists
            Queues (
                id INTEGER,
                project TEXT,
                name TEXT,
                metadata DOCUMENT,
                PRIMARY KEY(id),
                UNIQUE(project, name)
            )
        ''')

    def list(self, project, marker=None,
             limit=10, detailed=False):
        sql = (('''
            select name from Queues''' if not detailed
                else '''
            select name, metadata from Queues''') +
               '''
             where project = ?''')
        args = [project]

        if marker:
            sql += '''
               and name > ?'''
            args += [marker]

        sql += '''
             order by name
             limit ?'''
        args += [limit]

        records = self.driver.run(sql, *args)
        marker_name = {}

        def it():
            for rec in records:
                marker_name['next'] = rec[0]
                yield ({'name': rec[0]} if not detailed
                       else
                       {'name': rec[0], 'metadata': rec[1]})

        yield it()
        yield marker_name['next']

    def get(self, name, project):
        try:
            return self.driver.get('''
                select metadata from Queues
                 where project = ? and name = ?''', project, name)[0]

        except _NoResult:
            raise exceptions.QueueDoesNotExist(name, project)

    def upsert(self, name, metadata, project):
        with self.driver('immediate'):
            previous_record = self.driver.run('''
                select id from Queues
                 where project = ? and name = ?
            ''', project, name).fetchone()

            self.driver.run('''
                replace into Queues
                 values (null, ?, ?, ?)
            ''', project, name, self.driver.pack(metadata))

            return previous_record is None

    def delete(self, name, project):
        self.driver.run('''
            delete from Queues
             where project = ? and name = ?''', project, name)

    def stats(self, name, project):
        with self.driver('deferred'):
            qid = _get_qid(self.driver, name, project)
            claimed, free = self.driver.get('''
                select * from
                   (select count(msgid)
                      from Claims join Locked
                        on id = cid
                     where ttl > julianday() * 86400.0 - created
                       and qid = ?),
                   (select count(id)
                      from Messages left join Locked
                        on id = msgid
                     where msgid is null
                       and ttl > julianday() * 86400.0 - created
                       and qid = ?)
            ''', qid, qid)

            return {
                'messages': {
                    'claimed': claimed,
                    'free': free,
                },
                'actions': 0,
            }

    def actions(self, name, project, marker=None, limit=10):
        raise NotImplementedError


class Message(base.MessageBase):
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
        if not isinstance(message_ids, list):
            message_ids = [message_ids]

        message_ids = ["'%s'" % _msgid_decode(id) for id in message_ids]
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
                'id': id,
                'ttl': ttl,
                'age': int(age),
                'body': content,
            }

    def list(self, queue, project, marker=None,
             limit=10, echo=False, client_uuid=None):

        with self.driver('deferred'):
            sql = '''
                select id, content, ttl, julianday() * 86400.0 - created
                  from Messages
                 where ttl > julianday() * 86400.0 - created
                   and qid = ?'''
            args = [_get_qid(self.driver, queue, project)]

            if not echo:
                sql += '''
                   and client != ?'''
                args += [client_uuid]

            if marker:
                sql += '''
                   and id > ?'''
                args += [_marker_decode(marker)]

            sql += '''
                 limit ?'''
            args += [limit]

            records = self.driver.run(sql, *args)
            marker_id = {}

            def it():
                for id, content, ttl, age in records:
                    marker_id['next'] = id
                    yield {
                        'id': _msgid_encode(id),
                        'ttl': ttl,
                        'age': int(age),
                        'body': content,
                    }

            yield it()
            yield _marker_encode(marker_id['next'])

    def post(self, queue, messages, client_uuid, project):
        with self.driver('immediate'):
            qid = _get_qid(self.driver, queue, project)

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

        return map(_msgid_encode, range(unused, my['newid']))

    def delete(self, queue, message_id, project, claim=None):
        id = _msgid_decode(message_id)

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
        ''', id, _cid_decode(claim))

        if not self.driver.affected:
            raise exceptions.ClaimNotPermitted(_msgid_encode(id), claim)


class Claim(base.ClaimBase):
    def __init__(self, driver):
        self.driver = driver
        self.driver.run('''
            create table
            if not exists
            Claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                qid INTEGER,
                ttl INTEGER,
                created DATETIME,  -- seconds since the Julian day
                FOREIGN KEY(qid) references Queues(id) on delete cascade
            )
        ''')
        self.driver.run('''
            create table
            if not exists
            Locked (
                cid INTEGER,
                msgid INTEGER,
                FOREIGN KEY(cid) references Claims(id) on delete cascade,
                FOREIGN KEY(msgid) references Messages(id) on delete cascade
            )
        ''')

    def get(self, queue, claim_id, project):
        with self.driver('deferred'):
            try:
                id, ttl, age = self.driver.get('''
                    select C.id, C.ttl, julianday() * 86400.0 - C.created
                      from Queues as Q join Claims as C
                        on Q.id = C.qid
                     where C.ttl > julianday() * 86400.0 - C.created
                       and C.id = ? and project = ? and name = ?
                ''', _cid_decode(claim_id), project, queue)

                return (
                    {
                        'id': claim_id,
                        'ttl': ttl,
                        'age': int(age),
                    },
                    self.__get(id)
                )

            except (_NoResult, exceptions.MalformedID()):
                raise exceptions.ClaimDoesNotExist(claim_id, queue, project)

    def create(self, queue, metadata, project, limit=10):
        with self.driver('immediate'):
            qid = _get_qid(self.driver, queue, project)

            # cleanup all expired claims in this queue

            self.driver.run('''
                delete from Claims
                 where ttl <= julianday() * 86400.0 - created
                   and qid = ?''', qid)

            self.driver.run('''
                insert into Claims
                values (null, ?, ?, julianday() * 86400.0)
            ''', qid, metadata['ttl'])

            id = self.driver.lastrowid

            self.driver.run('''
                insert into Locked
                select last_insert_rowid(), id
                  from Messages left join Locked
                    on id = msgid
                 where msgid is null
                   and ttl > julianday() * 86400.0 - created
                   and qid = ?
                 limit ?''', qid, limit)

            self.__update_claimed(id, metadata['ttl'])

            return (_cid_encode(id), self.__get(id))

    def __get(self, cid):
        records = self.driver.run('''
            select id, content, ttl, julianday() * 86400.0 - created
              from Messages join Locked
                on msgid = id
             where ttl > julianday() * 86400.0 - created
               and cid = ?''', cid)

        for id, content, ttl, age in records:
            yield {
                'id': _msgid_encode(id),
                'ttl': ttl,
                'age': int(age),
                'body': content,
            }

    def update(self, queue, claim_id, metadata, project):
        try:
            id = _cid_decode(claim_id)
        except exceptions.MalformedID:
            raise exceptions.ClaimDoesNotExist(claim_id, queue, project)

        with self.driver('deferred'):

            # still delay the cleanup here
            self.driver.run('''
                update Claims
                   set created = julianday() * 86400.0,
                       ttl = ?
                 where ttl > julianday() * 86400.0 - created
                   and id = ?
                   and qid = (select id from Queues
                               where project = ? and name = ?)
            ''', metadata['ttl'], id, project, queue)

            if not self.driver.affected:
                raise exceptions.ClaimDoesNotExist(claim_id,
                                                   queue,
                                                   project)

            self.__update_claimed(id, metadata['ttl'])

    def __update_claimed(self, cid, ttl):
        # Precondition: cid is not expired
        self.driver.run('''
            update Messages
               set created = julianday() * 86400.0,
                   ttl = ?
             where ttl < ?
               and id in (select msgid from Locked
                           where cid = ?)
        ''', ttl, ttl, cid)

    def delete(self, queue, claim_id, project):
        try:
            cid = _cid_decode(claim_id)
        except exceptions.MalformedID:
            return

        self.driver.run('''
            delete from Claims
             where id = ?
               and qid = (select id from Queues
                           where project = ? and name = ?)
        ''', cid, project, queue)


class _NoResult(Exception):
    pass


def _get_qid(driver, queue, project):
    try:
        return driver.get('''
            select id from Queues
             where project = ? and name = ?''', project, queue)[0]

    except _NoResult:
        raise exceptions.QueueDoesNotExist(queue, project)


# The utilities below make the database IDs opaque to the users
# of Marconi API.  The only purpose is to advise the users NOT to
# make assumptions on the implementation of and/or relationship
# between the message IDs, the markers, and claim IDs.
#
# The magic numbers are arbitrarily picked; the numbers themselves
# come with no special functionalities.

def _msgid_encode(id):
    try:
        return hex(id ^ 0x5c693a53)[2:]

    except TypeError:
        raise exceptions.MalformedID()


def _msgid_decode(id):
    try:
        return int(id, 16) ^ 0x5c693a53

    except ValueError:
        raise exceptions.MalformedID()


def _marker_encode(id):
    return oct(id ^ 0x3c96a355)[1:]


def _marker_decode(id):
    try:
        return int(id, 8) ^ 0x3c96a355

    except ValueError:
        raise exceptions.MalformedMarker()


def _cid_encode(id):
    return hex(id ^ 0x63c9a59c)[2:]


def _cid_decode(id):
    try:
        return int(id, 16) ^ 0x63c9a59c

    except ValueError:
        raise exceptions.MalformedID()

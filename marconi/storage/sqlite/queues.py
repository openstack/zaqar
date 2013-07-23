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
from marconi.storage.sqlite import utils


class QueueController(base.QueueBase):
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

        if project is None:
            project = ''

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
        if project is None:
            project = ''

        try:
            return self.driver.get('''
                select metadata from Queues
                 where project = ? and name = ?''', project, name)[0]

        except utils.NoResult:
            raise exceptions.QueueDoesNotExist(name, project)

    def create(self, name, project):
        if project is None:
            project = ''

        # msgpack of {} is "\x80"
        self.driver.run('''
            insert or ignore into Queues
            values (null, ?, ?, "\x80")
        ''', project, name)

        return self.driver.affected

    def set_metadata(self, name, metadata, project):
        if project is None:
            project = ''

        self.driver.run('''
            update Queues
               set metadata = ?
             where project = ? and name = ?
        ''', self.driver.pack(metadata), project, name)

        if not self.driver.affected:
            raise exceptions.QueueDoesNotExist(name, project)

    def delete(self, name, project):
        if project is None:
            project = ''

        self.driver.run('''
            delete from Queues
             where project = ? and name = ?''', project, name)

    def stats(self, name, project):
        if project is None:
            project = ''

        with self.driver('deferred'):
            qid = utils.get_qid(self.driver, name, project)
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

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


import json

from marconi.storage import base
from marconi.storage import exceptions


class Queue(base.QueueBase):
    def __init__(self, driver):
        self.driver = driver
        self.driver._run('''create table if not exists Queues (
        id INTEGER,
        tenant TEXT,
        name TEXT,
        metadata TEXT,
        PRIMARY KEY(id),
        UNIQUE(tenant, name)
        )''')
        self.driver._run('''create unique index if not exists Paths on Queues (
        tenant, name
        )''')

    def list(self, tenant):
        records = self.driver._run('''select name, metadata from Queues where
                                      tenant = ?''', tenant)

        for k, v in records:
            yield {'name': k, 'metadata': v}

    def get(self, name, tenant):
        sql = '''select metadata from Queues where
                 tenant = ? and name = ?'''

        try:
            return json.loads(self.driver._get(sql, tenant, name)[0])
        except TypeError:
            msg = (_("Queue %(name)s does not exist for tenant %(tenant)s")
                   % dict(name=name, tenant=tenant))

            raise exceptions.DoesNotExist(msg)

    def upsert(self, name, metadata, tenant):
        with self.driver:
            sql_select = '''select metadata from Queues where
                            tenant = ? and name = ?'''
            previous_record = self.driver._get(sql_select, tenant, name)

            sql_replace = '''replace into Queues
                             values (null, ?, ?, ?)'''
            doc = json.dumps(metadata, ensure_ascii=False)
            self.driver._run(sql_replace, tenant, name, doc)

            return previous_record is None

    def delete(self, name, tenant):
        self.driver._run('''delete from Queues where
                            tenant = ? and name = ?''',
                         tenant, name)

    def stats(self, name, tenant):
        sql = '''select count(id)
                 from Messages where
                 qid = (select id from Queues where
                       tenant = ? and name = ?)'''

        return {
            'messages': self.driver._get(sql, tenant, name)[0],
            'actions': 0,
        }

    def actions(self, name, tenant, marker=None, limit=10):
        pass


class Message(base.MessageBase):
    def __init__(self, driver):
        self.driver = driver
        self.driver._run('''
            create table if not exists Messages (
                id INTEGER,
                qid INTEGER,
                ttl INTEGER,
                content TEXT,
                created DATETIME,
                PRIMARY KEY(id),
                FOREIGN KEY(qid) references Queues(id) on delete cascade
            )
        ''')

    def get(self, queue, tenant=None, message_id=None,
            marker=None, echo=False, client_uuid=None):
        pass

    def post(self, queue, messages, tenant):
        with self.driver:
            try:
                qid, = self.driver._get('''select id from Queues where
                                           tenant = ? and name = ?''',
                                        tenant, queue)
            except TypeError:
                msg = (_("Queue %(name)s does not exist for tenant %(tenant)s")
                       % dict(name=queue, tenant=tenant))

                raise exceptions.DoesNotExist(msg)

            # executemany() sets lastrowid to None, so no matter we manually
            # generate the IDs or not, we still need to query for it.
            try:
                unused, = self.driver._get('''select id + 1 from Messages
                                              where id = (select max(id)
                                              from Messages)''')
            except TypeError:
                unused, = 1001,

            def it(newid):
                for m in messages:
                    yield (newid, qid, m['ttl'],
                           json.dumps(m, ensure_ascii=False))

                    newid += 1

            self.driver._run_multiple('''insert into Messages values
                                         (?, ?, ?, ?, datetime())''',
                                      it(unused))

        return [str(x) for x in range(unused, unused + len(messages))]

    def delete(self, queue, message_id, tenant=None, claim=None):
        pass

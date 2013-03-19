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
        ans = []
        for rec in self.driver._run('''select name from Queues where
                tenant = ?''', tenant):
            ans.append(rec[0])
        return ans

    def get(self, name, tenant):
        try:
            return json.loads(
                self.driver._get('''select metadata from Queues where
                    tenant = ? and name = ?''', tenant, name)[0])
        except TypeError:
            raise exceptions.DoesNotExist('/'.join([tenant, 'queues', name]))

    def upsert(self, name, metadata, tenant):
        with self.driver:
            rc = self.driver._get('''select metadata from Queues where
                    tenant = ? and name = ?''', tenant, name) is None
            self.driver._run('''replace into Queues values
                    (null, ?, ?, ?)''', tenant, name,
                    json.dumps(metadata))
            return rc

    def delete(self, name, tenant):
        self.driver._run('''delete from Queues where
                tenant = ? and name = ?''', tenant, name)

    def stats(self, name, tenant):
        return {'messages': self.driver._get('''select count(id)
                from Messages where
                qid = (select id from Queues where
                       tenant = ? and name = ?)''', tenant, name)[0],
                'actions': 0}

    def actions(self, name, tenant, marker=None, limit=10):
        pass


class Message(base.MessageBase):
    def __init__(self, driver):
        self.driver = driver
        self.driver._run('''create table if not exists Messages (
        id INTEGER,
        qid INTEGER,
        ttl INTEGER,
        content TEXT,
        created DATETIME,
        PRIMARY KEY(id),
        FOREIGN KEY(qid) references Queues(id) on delete cascade
        )''')

    def get(self, queue, tenant=None, message_id=None,
            marker=None, echo=False, client_uuid=None):
        pass

    def post(self, queue, messages, tenant):
        with self.driver:
            try:
                qid, = self.driver._get('''select id from Queues where
                        tenant = ? and name = ?''', tenant, queue)
            except TypeError:
                raise exceptions.DoesNotExist(
                        '/'.join([tenant, 'queues', queue]))
            try:
                newid = self.driver._get('''select id + 1 from Messages
                        where id = (select max(id) from Messages)''')[0]
            except TypeError:
                newid = 1001
            for m in messages:
                self.driver._run('''insert into Messages values
                        (?, ?, ?, ?, datetime())''',
                        newid, qid, m['ttl'], json.dumps(m))
                newid += 1
        return [str(x) for x in range(newid - len(messages), newid)]

    def delete(self, queue, message_id, tenant=None, claim=None):
        pass

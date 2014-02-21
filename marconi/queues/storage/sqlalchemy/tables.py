# Copyright (c) 2013 Red Hat, Inc.
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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import sqlalchemy as sa

metadata = sa.MetaData()


'''
create table
if not exists
Messages (
    id INTEGER,
    qid INTEGER,
    ttl INTEGER,
    body DOCUMENT,
    client TEXT,
    created DATETIME,
    PRIMARY KEY(id),
    FOREIGN KEY(qid) references Queues(id) on delete cascade
)
'''
Messages = sa.Table('Messages', metadata,
                    sa.Column('id', sa.INTEGER, primary_key=True),
                    sa.Column('qid', sa.INTEGER,
                              sa.ForeignKey("Queues.id", ondelete="CASCADE"),
                              nullable=False),
                    sa.Column('ttl', sa.INTEGER),
                    sa.Column('body', sa.LargeBinary),
                    sa.Column('client', sa.TEXT),
                    sa.Column('created', sa.DATETIME),
                    )


'''
create table
if not exists
Claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    qid INTEGER,
    ttl INTEGER,
    created DATETIME,
    FOREIGN KEY(qid) references Queues(id) on delete cascade
)
'''
Claims = sa.Table('Claims', metadata,
                  sa.Column('id', sa.INTEGER, primary_key=True,
                            autoincrement=True),
                  sa.Column('qid', sa.INTEGER,
                            sa.ForeignKey("Queues.id", ondelete="CASCADE"),
                            nullable=False),
                  sa.Column('ttl', sa.INTEGER),
                  sa.Column('created', sa.DATETIME),
                  )


'''
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
'''
Queues = sa.Table('Queues', metadata,
                  sa.Column('id', sa.INTEGER, primary_key=True),
                  sa.Column('project', sa.String),
                  sa.Column('name', sa.String),
                  sa.Column('metadata', sa.LargeBinary),
                  sa.UniqueConstraint('project', 'name'),
                  )


'''
create table
if not exists
Locked (
    cid INTEGER,
    msgid INTEGER,
    FOREIGN KEY(cid) references Claims(id) on delete cascade,
    FOREIGN KEY(msgid) references Messages(id) on delete cascade
)
'''
Locked = sa.Table('Locked', metadata,
                  sa.Column('cid', sa.INTEGER,
                            sa.ForeignKey("Claims.id", ondelete="CASCADE"),
                            nullable=False),
                  sa.Column('msgid', sa.INTEGER,
                            sa.ForeignKey("Messages.id", ondelete="CASCADE"),
                            nullable=False),
                  )

Shards = sa.Table('Shards', metadata,
                  sa.Column('name', sa.String, primary_key=True),
                  sa.Column('uri', sa.String, nullable=False),
                  sa.Column('weight', sa.INTEGER, nullable=False),
                  sa.Column('options', sa.BINARY))

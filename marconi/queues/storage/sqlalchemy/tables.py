# Copyright (c) 2013 Red Hat, Inc.
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

import sqlalchemy as sa

from marconi.openstack.common import timeutils

metadata = sa.MetaData()

now = timeutils.utcnow


Messages = sa.Table('Messages', metadata,
                    sa.Column('id', sa.INTEGER, primary_key=True),
                    sa.Column('qid', sa.INTEGER,
                              sa.ForeignKey("Queues.id", ondelete="CASCADE"),
                              nullable=False),
                    sa.Column('ttl', sa.INTEGER),
                    sa.Column('body', sa.LargeBinary),
                    sa.Column('client', sa.TEXT),
                    sa.Column('created', sa.TIMESTAMP,
                              default=now, onupdate=now),
                    sa.Column('cid', sa.INTEGER,
                              sa.ForeignKey("Claims.id", ondelete='SET NULL')),
                    )


Claims = sa.Table('Claims', metadata,
                  sa.Column('id', sa.INTEGER, primary_key=True,
                            autoincrement=True),
                  sa.Column('qid', sa.INTEGER,
                            sa.ForeignKey("Queues.id", ondelete="CASCADE"),
                            nullable=False),
                  sa.Column('ttl', sa.INTEGER),
                  sa.Column('created', sa.TIMESTAMP,
                            default=now, onupdate=now),
                  )


Queues = sa.Table('Queues', metadata,
                  sa.Column('id', sa.INTEGER, primary_key=True),
                  sa.Column('project', sa.String(64)),
                  sa.Column('name', sa.String(64)),
                  sa.Column('metadata', sa.LargeBinary),
                  sa.UniqueConstraint('project', 'name'),
                  )


Shards = sa.Table('Shards', metadata,
                  sa.Column('name', sa.String(64), primary_key=True),
                  sa.Column('uri', sa.String(255), nullable=False),
                  sa.Column('weight', sa.INTEGER, nullable=False),
                  sa.Column('options', sa.BINARY))


Catalogue = sa.Table('Catalogue', metadata,
                     sa.Column('shard', sa.String(64),
                               sa.ForeignKey('Shards.name',
                                             ondelete='CASCADE'),
                               primary_key=True),
                     sa.Column('project', sa.String(64), nullable=False),
                     sa.Column('queue', sa.String(64), nullable=False),
                     sa.UniqueConstraint('project', 'queue'))

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

metadata = sa.MetaData()

Queues = sa.Table('Queues', metadata,
                  sa.Column('id', sa.INTEGER, primary_key=True),
                  sa.Column('project', sa.String(64)),
                  sa.Column('name', sa.String(64)),
                  sa.Column('metadata', sa.LargeBinary),
                  sa.UniqueConstraint('project', 'name'),
                  )

Pools = sa.Table('Pools', metadata,
                 sa.Column('name', sa.String(64), primary_key=True),
                 sa.Column('uri', sa.String(255),
                           unique=True, nullable=False),
                 sa.Column('weight', sa.INTEGER, nullable=False),
                 sa.Column('options', sa.Text()),
                 sa.Column('flavor', sa.String(64), nullable=True))

# NOTE(gengchc2): Modify pool_group define: turn NOT NULL into DEFAULT NULL:
# [alter table Flavors change column pool_group pool_group varchar(64)
# default null;]
Flavors = sa.Table('Flavors', metadata,
                   sa.Column('name', sa.String(64), primary_key=True),
                   sa.Column('project', sa.String(64)),
                   sa.Column('capabilities', sa.Text()))

Catalogue = sa.Table('Catalogue', metadata,
                     sa.Column('pool', sa.String(64),
                               sa.ForeignKey('Pools.name',
                                             ondelete='CASCADE')),
                     sa.Column('project', sa.String(64)),
                     sa.Column('queue', sa.String(64), nullable=False),
                     sa.UniqueConstraint('project', 'queue'))

# Copyright 2016 OpenStack Foundation.
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

"""Liberty release

Revision ID: 001
Revises: None
Create Date: 2015-09-13 20:46:25.783444

"""

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None

from alembic import op
import sqlalchemy as sa

MYSQL_ENGINE = 'InnoDB'
MYSQL_CHARSET = 'utf8'


def upgrade():
    op.create_table('Queues',
                    sa.Column('id', sa.INTEGER, primary_key=True),
                    sa.Column('project', sa.String(64)),
                    sa.Column('name', sa.String(64)),
                    sa.Column('metadata', sa.LargeBinary),
                    sa.UniqueConstraint('project', 'name'))

    op.create_table('PoolGroup',
                    sa.Column('name', sa.String(64), primary_key=True))

    op.create_table('Pools',
                    sa.Column('name', sa.String(64), primary_key=True),
                    sa.Column('group', sa.String(64),
                              sa.ForeignKey('PoolGroup.name',
                                            ondelete='CASCADE'),
                              nullable=True),
                    sa.Column('uri', sa.String(255),
                              unique=True, nullable=False),
                    sa.Column('weight', sa.INTEGER, nullable=False),
                    sa.Column('options', sa.Text()))

    op.create_table('Flavors',
                    sa.Column('name', sa.String(64), primary_key=True),
                    sa.Column('project', sa.String(64)),
                    sa.Column('pool_group', sa.String(64),
                              sa.ForeignKey('PoolGroup.name',
                                            ondelete='CASCADE'),
                              nullable=False),
                    sa.Column('capabilities', sa.Text()))

    op.create_table('Catalogue',
                    sa.Column('pool', sa.String(64),
                              sa.ForeignKey('Pools.name',
                                            ondelete='CASCADE')),
                    sa.Column('project', sa.String(64)),
                    sa.Column('queue', sa.String(64), nullable=False),
                    sa.UniqueConstraint('project', 'queue'))

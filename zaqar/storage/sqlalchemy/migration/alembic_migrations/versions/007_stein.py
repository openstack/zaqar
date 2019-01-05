# Copyright 2017 ZTE Corporation.
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

"""Stein release

Revision ID: 006
Revises: 007
Create Date: 2019-01-09 11:45:45.928605

"""

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'

from alembic import op
import sqlalchemy as sa

MYSQL_ENGINE = 'InnoDB'
MYSQL_CHARSET = 'utf8'


def upgrade():
    op.drop_constraint(constraint_name='Pools_ibfk_1',
                       table_name='Pools',
                       type_='foreignkey')
    op.drop_constraint(constraint_name='Flavors_ibfk_1',
                       table_name='Flavors',
                       type_='foreignkey')
    op.drop_column('Pools', 'group')
    op.drop_column('Flavors', 'pool_group')
    op.execute('drop table PoolGroup ')


def downgrade():
    op.add_column('Pools', sa.Column('group', sa.String(64), nullable=True))
    op.add_column('Flavors',
                  sa.Column('pool_group', sa.String(64), nullable=True))
    op.create_table('PoolGroup',
                    sa.Column('name', sa.String(64), primary_key=True))

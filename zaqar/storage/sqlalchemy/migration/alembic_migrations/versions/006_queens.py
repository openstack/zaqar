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

"""Queens release

Revision ID: 005
Revises: 006
Create Date: 2017-11-09 11:45:45.928605

"""

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'

from alembic import op
import sqlalchemy as sa

MYSQL_ENGINE = 'InnoDB'
MYSQL_CHARSET = 'utf8'


def upgrade():
    # NOTE(gengchc2): Add a new flavor column to Pools nodes
    op.add_column('Pools', sa.Column('flavor', sa.String(64), nullable=True))

    # NOTE(gengchc2): Change pool_group to default null in Flavors table
    op.execute('alter table Flavors change column pool_group '
               'pool_group varchar(64) default null')

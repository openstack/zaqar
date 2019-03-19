# Copyright (c) 2015 OpenStack Foundation.
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

"""flavors: an implementation of the flavor management storage
controller for sqlalchemy.

"""

import oslo_db.exception
import sqlalchemy as sa

from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.sqlalchemy import tables
from zaqar.storage.sqlalchemy import utils


class FlavorsController(base.FlavorsBase):

    def __init__(self, *args, **kwargs):
        super(FlavorsController, self).__init__(*args, **kwargs)
        self._pools_ctrl = self.driver.pools_controller

    @utils.raises_conn_error
    def list(self, project=None, marker=None, limit=10, detailed=False):
        marker = marker or ''

        # TODO(cpp-cabrera): optimization - limit the columns returned
        # when detailed=False by specifying them in the select()
        # clause
        stmt = sa.sql.select([tables.Flavors]).where(
            sa.and_(tables.Flavors.c.name > marker,
                    tables.Flavors.c.project == project)
        )

        if limit > 0:
            stmt = stmt.limit(limit)
        cursor = self.driver.run(stmt)

        marker_name = {}

        def it():
            for cur in cursor:
                marker_name['next'] = cur[0]
                yield _normalize(cur, detailed=detailed)

        yield it()
        yield marker_name and marker_name['next']

    @utils.raises_conn_error
    def get(self, name, project=None, detailed=False):
        stmt = sa.sql.select([tables.Flavors]).where(
            sa.and_(tables.Flavors.c.name == name,
                    tables.Flavors.c.project == project)
        )

        flavor = self.driver.run(stmt).fetchone()
        if flavor is None:
            raise errors.FlavorDoesNotExist(name)

        return _normalize(flavor, detailed)

    @utils.raises_conn_error
    def create(self, name, project=None, capabilities=None):
        cap = None if capabilities is None else utils.json_encode(capabilities)

        try:
            stmt = sa.sql.expression.insert(tables.Flavors).values(
                name=name, project=project,
                capabilities=cap
            )
            self.driver.run(stmt)
        except oslo_db.exception.DBDuplicateEntry:
            # TODO(flaper87): merge update/create into a single
            # method with introduction of upsert
            self.update(name,
                        project=project,
                        capabilities=capabilities)

    @utils.raises_conn_error
    def exists(self, name, project=None):
        stmt = sa.sql.select([tables.Flavors.c.name]).where(
            sa.and_(tables.Flavors.c.name == name,
                    tables.Flavors.c.project == project)
        ).limit(1)
        return self.driver.run(stmt).fetchone() is not None

    @utils.raises_conn_error
    def update(self, name, project=None, capabilities=None):
        fields = {}

        if capabilities is not None:
            fields['capabilities'] = capabilities

        assert fields, '`capabilities` not found in kwargs'
        if 'capabilities' in fields:
            fields['capabilities'] = utils.json_encode(fields['capabilities'])

        stmt = sa.sql.update(tables.Flavors).where(
            sa.and_(tables.Flavors.c.name == name,
                    tables.Flavors.c.project == project)).values(**fields)

        res = self.driver.run(stmt)
        if res.rowcount == 0:
            raise errors.FlavorDoesNotExist(name)

    @utils.raises_conn_error
    def delete(self, name, project=None):
        stmt = sa.sql.expression.delete(tables.Flavors).where(
            sa.and_(tables.Flavors.c.name == name,
                    tables.Flavors.c.project == project)
        )
        self.driver.run(stmt)

    @utils.raises_conn_error
    def drop_all(self):
        stmt = sa.sql.expression.delete(tables.Flavors)
        self.driver.run(stmt)


def _normalize(flavor, detailed=False):
    ret = {
        'name': flavor[0],
    }

    if detailed:
        capabilities = flavor[2]
        ret['capabilities'] = (utils.json_decode(capabilities)
                               if capabilities else {})

    return ret

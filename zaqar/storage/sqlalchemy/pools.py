# Copyright (c) 2014 Rackspace, Inc.
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

"""pools: an implementation of the pool management storage
controller for sqlalchemy.

"""

import functools

import oslo_db.exception
import sqlalchemy as sa

from zaqar.common import utils as common_utils
from zaqar.storage import base
from zaqar.storage import errors
from zaqar.storage.sqlalchemy import tables
from zaqar.storage.sqlalchemy import utils


class PoolsController(base.PoolsBase):

    @utils.raises_conn_error
    def _list(self, marker=None, limit=10, detailed=False):
        marker = marker or ''

        # TODO(cpp-cabrera): optimization - limit the columns returned
        # when detailed=False by specifying them in the select()
        # clause
        stmt = sa.sql.select([tables.Pools]).where(
            tables.Pools.c.name > marker
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
    def _get_pools_by_group(self, group=None, detailed=False):
        stmt = sa.sql.select([tables.Pools]).where(
            tables.Pools.c.group == group
        )
        cursor = self.driver.run(stmt)

        normalizer = functools.partial(_normalize, detailed=detailed)
        return (normalizer(v) for v in cursor)

    @utils.raises_conn_error
    def _get(self, name, detailed=False):
        stmt = sa.sql.select([tables.Pools]).where(
            tables.Pools.c.name == name
        )

        pool = self.driver.run(stmt).fetchone()
        if pool is None:
            raise errors.PoolDoesNotExist(name)

        return _normalize(pool, detailed)

    def _ensure_group_exists(self, name):
        try:
            stmt = sa.sql.expression.insert(tables.PoolGroup).values(name=name)
            self.driver.run(stmt)
            return True
        except oslo_db.exception.DBDuplicateEntry:
            return False

    # TODO(cpp-cabrera): rename to upsert
    @utils.raises_conn_error
    def _create(self, name, weight, uri, group=None, options=None):
        opts = None if options is None else utils.json_encode(options)

        if group is not None:
            self._ensure_group_exists(group)

        try:
            stmt = sa.sql.expression.insert(tables.Pools).values(
                name=name, weight=weight, uri=uri, group=group, options=opts
            )
            self.driver.run(stmt)

        except oslo_db.exception.DBDuplicateEntry:
            # TODO(cpp-cabrera): merge update/create into a single
            # method with introduction of upsert
            self._update(name, weight=weight, uri=uri,
                         group=group, options=options)

    @utils.raises_conn_error
    def _exists(self, name):
        stmt = sa.sql.select([tables.Pools.c.name]).where(
            tables.Pools.c.name == name
        ).limit(1)
        return self.driver.run(stmt).fetchone() is not None

    @utils.raises_conn_error
    def _update(self, name, **kwargs):
        # NOTE(cpp-cabrera): by pruning None-valued kwargs, we avoid
        # overwriting the existing options field with None, since that
        # one can be null.
        names = ('uri', 'weight', 'group', 'options')
        fields = common_utils.fields(kwargs, names,
                                     pred=lambda x: x is not None)

        assert fields, ('`weight`, `uri`, `group`, '
                        'or `options` not found in kwargs')

        if 'options' in fields:
            fields['options'] = utils.json_encode(fields['options'])

        if fields.get('group') is not None:
            self._ensure_group_exists(fields.get('group'))

        stmt = sa.sql.update(tables.Pools).where(
            tables.Pools.c.name == name).values(**fields)

        res = self.driver.run(stmt)
        if res.rowcount == 0:
            raise errors.PoolDoesNotExist(name)

    @utils.raises_conn_error
    def _delete(self, name):
        stmt = sa.sql.expression.delete(tables.Pools).where(
            tables.Pools.c.name == name
        )
        self.driver.run(stmt)

    @utils.raises_conn_error
    def _drop_all(self):
        stmt = sa.sql.expression.delete(tables.Pools)
        self.driver.run(stmt)
        stmt = sa.sql.expression.delete(tables.PoolGroup)
        self.driver.run(stmt)


def _normalize(pool, detailed=False):
    ret = {
        'name': pool[0],
        'group': pool[1],
        'uri': pool[2],
        'weight': pool[3],
    }
    if detailed:
        opts = pool[4]
        ret['options'] = utils.json_decode(opts) if opts else {}

    return ret

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

"""shards: an implementation of the shard management storage
controller for sqlalchemy.

Schema:
  'n': name :: six.text_type
  'u': uri :: six.text_type
  'w': weight :: int
  'o': options :: dict
"""

import functools
import json

import sqlalchemy as sa

from marconi.common import utils as common_utils
from marconi.queues.storage import base
from marconi.queues.storage import errors
from marconi.queues.storage.sqlalchemy import tables
from marconi.queues.storage.sqlalchemy import utils


class ShardsController(base.ShardsBase):

    def __init__(self, *args, **kwargs):
        super(ShardsController, self).__init__(*args, **kwargs)

        self._conn = self.driver.connection

    @utils.raises_conn_error
    def list(self, marker=None, limit=10, detailed=False):
        marker = marker or ''

        # TODO(cpp-cabrera): optimization - limit the columns returned
        # when detailed=False by specifying them in the select()
        # clause
        stmt = sa.sql.select([tables.Shards]).where(
            tables.Shards.c.name > marker
        ).limit(limit)
        cursor = self._conn.execute(stmt)

        normalizer = functools.partial(_normalize, detailed=detailed)
        return (normalizer(v) for v in cursor)

    @utils.raises_conn_error
    def get(self, name, detailed=False):
        stmt = sa.sql.select([tables.Shards]).where(
            tables.Shards.c.name == name
        )

        shard = self._conn.execute(stmt).fetchone()
        if shard is None:
            raise errors.ShardDoesNotExist(name)

        return _normalize(shard, detailed)

    # TODO(cpp-cabrera): rename to upsert
    @utils.raises_conn_error
    def create(self, name, weight, uri, options=None):
        opts = None if options is None else json.dumps(options)

        try:
            stmt = sa.sql.expression.insert(tables.Shards).values(
                name=name, weight=weight, uri=uri, options=opts
            )
            self._conn.execute(stmt)

        except sa.exc.IntegrityError:
            # TODO(cpp-cabrera): merge update/create into a single
            # method with introduction of upsert
            self.update(name, weight=weight, uri=uri,
                        options=options)

    @utils.raises_conn_error
    def exists(self, name):
        stmt = sa.sql.select([tables.Shards.c.name]).where(
            tables.Shards.c.name == name
        ).limit(1)
        return self._conn.execute(stmt).fetchone() is not None

    @utils.raises_conn_error
    def update(self, name, **kwargs):
        # NOTE(cpp-cabrera): by pruning None-valued kwargs, we avoid
        # overwriting the existing options field with None, since that
        # one can be null.
        names = ('uri', 'weight', 'options')
        fields = common_utils.fields(kwargs, names,
                                     pred=lambda x: x is not None)

        assert fields, '`weight`, `uri`, or `options` not found in kwargs'

        if 'options' in fields:
            fields['options'] = json.dumps(fields['options'])

        stmt = sa.sql.update(tables.Shards).where(
            tables.Shards.c.name == name).values(**fields)

        res = self._conn.execute(stmt)
        if res.rowcount == 0:
            raise errors.ShardDoesNotExist(name)

    @utils.raises_conn_error
    def delete(self, name):
        stmt = sa.sql.expression.delete(tables.Shards).where(
            tables.Shards.c.name == name
        )
        self._conn.execute(stmt)

    @utils.raises_conn_error
    def drop_all(self):
        stmt = sa.sql.expression.delete(tables.Shards)
        self._conn.execute(stmt)


def _normalize(shard, detailed=False):
    ret = {
        'name': shard[0],
        'uri': shard[1],
        'weight': shard[2],
    }
    if detailed:
        opts = shard[3]
        ret['options'] = json.loads(opts) if opts else None

    return ret

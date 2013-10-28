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
#
# See the License for the specific language governing permissions and
# limitations under the License.

from marconi.queues.storage import base
from marconi.queues.storage import errors
from marconi.queues.storage.sqlite import utils


class QueueController(base.QueueBase):

    def list(self, project, marker=None,
             limit=None, detailed=False):

        if project is None:
            project = ''

        if limit is None:
            limit = self.driver.limits_conf.default_queue_paging

        sql = (('''
            select name from Queues''' if not detailed
                else '''
            select name, metadata from Queues''') +
               '''
             where project = ?''')
        args = [project]

        if marker:
            sql += '''
               and name > ?'''
            args += [marker]

        sql += '''
             order by name
             limit ?'''
        args += [limit]

        records = self.driver.run(sql, *args)
        marker_name = {}

        def it():
            for rec in records:
                marker_name['next'] = rec[0]
                yield ({'name': rec[0]} if not detailed
                       else
                       {'name': rec[0], 'metadata': rec[1]})

        yield it()
        yield marker_name['next']

    def get_metadata(self, name, project):
        if project is None:
            project = ''

        try:
            return self.driver.get('''
                select metadata from Queues
                 where project = ? and name = ?''', project, name)[0]

        except utils.NoResult:
            raise errors.QueueDoesNotExist(name, project)

    def create(self, name, project):
        if project is None:
            project = ''

        # msgpack of {} is "\x80"
        self.driver.run('''
            insert or ignore into Queues
            values (null, ?, ?, "\x80")
        ''', project, name)

        return self.driver.affected

    def exists(self, name, project):
        if project is None:
            project = ''

        return self.driver.run('''
            select id from Queues
             where project = ? and name = ?
        ''', project, name).fetchone() is not None

    def set_metadata(self, name, metadata, project):
        if project is None:
            project = ''

        self.driver.run('''
            update Queues
               set metadata = ?
             where project = ? and name = ?
        ''', self.driver.pack(metadata), project, name)

        if not self.driver.affected:
            raise errors.QueueDoesNotExist(name, project)

    def delete(self, name, project):
        if project is None:
            project = ''

        self.driver.run('''
            delete from Queues
             where project = ? and name = ?''', project, name)

    def stats(self, name, project):
        if project is None:
            project = ''

        with self.driver('deferred'):
            qid = utils.get_qid(self.driver, name, project)
            claimed, free = self.driver.get('''
                select * from
                   (select count(msgid)
                      from Claims join Locked
                        on id = cid
                     where ttl > julianday() * 86400.0 - created
                       and qid = ?),
                   (select count(id)
                      from Messages left join Locked
                        on id = msgid
                     where msgid is null
                       and ttl > julianday() * 86400.0 - created
                       and qid = ?)
            ''', qid, qid)

            total = free + claimed

            message_stats = {
                'claimed': claimed,
                'free': free,
                'total': total,
            }

            try:
                message_controller = self.driver.message_controller
                oldest = message_controller.first(name, project, sort=1)
                newest = message_controller.first(name, project, sort=-1)
            except errors.QueueIsEmpty:
                pass
            else:
                message_stats['oldest'] = utils.stat_message(oldest)
                message_stats['newest'] = utils.stat_message(newest)

            return {'messages': message_stats}

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
# See the License for the specific language governing permissions and
# limitations under the License.

import testtools

from marconi.storage import exceptions
from marconi.storage import sqlite
from marconi.tests.util import suite


class TestSqlite(suite.TestSuite):

    def test_sqlite(self):
        storage = sqlite.Driver()
        q = storage.queue_controller
        self.assertEquals(q.upsert('fizbit', {'_message_ttl': 40}, '480924'),
                True)
        q.upsert('boomerang', {}, '480924')
        q.upsert('boomerang', {}, '01314')
        q.upsert('unrelated', {}, '01314')
        self.assertEquals(set(q.list('480924')), set(['fizbit', 'boomerang']))
        with testtools.ExpectedException(exceptions.DoesNotExist):
            q.get('Fizbit', '480924')
        self.assertEquals(q.upsert('fizbit', {'_message_ttl': 20}, '480924'),
                False)
        self.assertEquals(q.get('fizbit', '480924'), {'_message_ttl': 20})
        q.delete('boomerang', '480924')
        with testtools.ExpectedException(exceptions.DoesNotExist):
            q.get('boomerang', '480924')

        m = storage.message_controller
        d = [
                {"body": {
                    "event": "BackupStarted",
                    "backupId": "c378813c-3f0b-11e2-ad92-7823d2b0f3ce"
                },
                'ttl': 30
                },
                {"body": {
                "event": "BackupProgress",
                "currentBytes": "0",
                "totalBytes": "99614720"
                },
                'ttl': 10
                }
            ]
        n = q.stats('fizbit', '480924')['messages']
        l1 = m.post('fizbit', d, '480924')
        l2 = m.post('fizbit', d, '480924')
        self.assertEquals([int(v) + 2 for v in l1], map(int, l2))
        self.assertEquals(q.stats('fizbit', '480924')['messages'] - n, 4)
        q.delete('fizbit', '480924')
        with testtools.ExpectedException(exceptions.DoesNotExist):
            m.post('fizbit', d, '480924')

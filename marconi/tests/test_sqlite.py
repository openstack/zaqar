# Copyright (c) 2013 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from marconi.storage import exceptions
from marconi.storage import sqlite
from marconi.tests import util as testing


#TODO(zyuan): let tests/storage/base.py handle these
class TestSqlite(testing.TestBase):

    def setUp(self):
        super(TestSqlite, self).setUp()

        storage = sqlite.Driver()
        self.queue_ctrl = storage.queue_controller
        self.queue_ctrl.upsert('fizbit', {'_message_ttl': 40}, '480924')
        self.msg_ctrl = storage.message_controller
        self.claim_ctrl = storage.claim_controller

    def test_some_messages(self):
        doc = [
            {
                'body': {
                    'event': 'BackupStarted',
                    'backupId': 'c378813c-3f0b-11e2-ad92-7823d2b0f3ce',
                },
                'ttl': 30,
            },
        ]

        for _ in range(10):
            self.msg_ctrl.post('fizbit', doc,
                               tenant='480924',
                               client_uuid='30387f00')
        msgid = self.msg_ctrl.post('fizbit', doc,
                                   tenant='480924',
                                   client_uuid='79ed56f8')[0]

        countof = self.queue_ctrl.stats('fizbit', '480924')
        self.assertEquals(countof['messages']['total'], 11)

        msgs = list(self.msg_ctrl.list('fizbit', '480924',
                                       echo=True,
                                       limit=20))

        self.assertEquals(len(msgs), 11)

        msgs = list(self.msg_ctrl.list('fizbit', '480924',
                                       client_uuid='30387f00'))

        self.assertEquals(len(msgs), 1)

        #TODO(zyuan): move this to tests/storage/test_impl_sqlite.py
        msgs = list(self.msg_ctrl.list('fizbit', '480924',
                                       marker='illformed'))

        self.assertEquals(len(msgs), 0)

        cnt = 0
        marker = None
        while True:
            nomsg = True
            for msg in self.msg_ctrl.list('fizbit', '480924',
                                          limit=3, marker=marker,
                                          client_uuid='79ed56f8'):
                nomsg = False
            if nomsg:
                break
            marker = msg['marker']
            cnt += 1

        self.assertEquals(cnt, 4)

        # can not delete a message with a wrong claim
        cid_another, _ = self.claim_ctrl.create(
            'fizbit', {'ttl': 10}, '480924')

        with testing.expected(exceptions.NotPermitted):
            self.msg_ctrl.delete('fizbit', msgid, '480924', cid_another)

        # ensure the message counts
        countof = self.queue_ctrl.stats('fizbit', '480924')
        self.assertEquals(countof['messages']['total'], 11)
        self.assertEquals(countof['messages']['claimed'], 10)

        # claim a message
        cid, msgs = self.claim_ctrl.create('fizbit', {'ttl': 10}, '480924')

        self.assertEquals(len(list(msgs)), 1)

        # delete a message under a claim
        self.msg_ctrl.delete('fizbit', msgid, '480924', cid)

        with testing.expected(exceptions.DoesNotExist):
            self.msg_ctrl.get('fizbit', msgid, '480924')

        meta, msgs = self.claim_ctrl.get('fizbit', cid, '480924')

        self.assertEquals(len(list(msgs)), 0)

        # it's just fine to delete a non-existing message
        self.msg_ctrl.delete('fizbit', msgid, '480924')

        # claim expires
        self.claim_ctrl.update('fizbit', meta['id'], {'ttl': 0}, '480924')

        with testing.expected(exceptions.DoesNotExist):
            self.claim_ctrl.get('fizbit', meta['id'], '480924')

        with testing.expected(exceptions.DoesNotExist):
            self.claim_ctrl.update('fizbit', meta['id'], {'ttl': 40}, '480924')

        # delete a claim
        self.claim_ctrl.delete('fizbit', cid_another, '480924')

        with testing.expected(exceptions.DoesNotExist):
            self.claim_ctrl.get('fizbit', cid_another, '480924')

    def test_expired_messages(self):
        doc = [
            {'body': {}, 'ttl': 0},
        ]

        msgid = self.msg_ctrl.post('fizbit', doc,
                                   tenant='480924',
                                   client_uuid='unused')[0]

        with testing.expected(exceptions.DoesNotExist):
            self.msg_ctrl.get('fizbit', msgid, '480924')

        countof = self.queue_ctrl.stats('fizbit', '480924')
        self.assertEquals(countof['messages']['expired'], 1)

    def test_nonexsitent(self):
        with testing.expected(exceptions.DoesNotExist):
            self.msg_ctrl.post('nonexistent', [],
                               tenant='480924',
                               client_uuid='30387f00')

        with testing.expected(exceptions.DoesNotExist):
            for _ in self.msg_ctrl.list('nonexistent', '480924'):
                pass

        with testing.expected(exceptions.DoesNotExist):
            self.queue_ctrl.stats('nonexistent', '480924')

    #TODO(zyuan): move this to tests/storage/test_impl_sqlite.py
    def test_illformed_id(self):

        # SQlite-specific tests.  Since all IDs exposed in APIs are opaque,
        # any ill-formed IDs should be regarded as non-existing ones.

        with testing.expected(exceptions.DoesNotExist):
            self.msg_ctrl.get('nonexistent', 'illformed', '480924')

        self.claim_ctrl.delete('nonexistent', 'illformed', '480924')

        with testing.expected(exceptions.DoesNotExist):
            self.claim_ctrl.update('nonexistent', 'illformed',
                                   {'ttl': 40}, '480924')

    def tearDown(self):
        self.queue_ctrl.delete('fizbit', '480924')

        super(TestSqlite, self).tearDown()

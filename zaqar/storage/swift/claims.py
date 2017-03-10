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

import hashlib
import math

from oslo_serialization import jsonutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
import swiftclient

from zaqar.common import decorators
from zaqar import storage
from zaqar.storage import errors
from zaqar.storage.swift import utils


class ClaimController(storage.Claim):
    """Implements claims resource operations with swift backend

    Claims are scoped by project + queue.
    """
    def __init__(self, *args, **kwargs):
        super(ClaimController, self).__init__(*args, **kwargs)
        self._client = self.driver.connection

    @decorators.lazy_property(write=False)
    def _message_ctrl(self):
        return self.driver.message_controller

    @decorators.lazy_property(write=False)
    def _queue_ctrl(self):
        return self.driver.queue_controller

    def _exists(self, queue, claim_id, project=None):
        try:
            return self._client.head_object(
                utils._claim_container(queue, project),
                claim_id)
        except swiftclient.ClientException as exc:
            if exc.http_status == 404:
                raise errors.ClaimDoesNotExist(claim_id, queue, project)
            raise

    def _get(self, queue, claim_id, project=None):
        try:
            container = utils._claim_container(queue, project)
            headers, claim = self._client.get_object(container, claim_id)
        except swiftclient.ClientException as exc:
            if exc.http_status != 404:
                raise
            return
        now = timeutils.utcnow_ts(True)
        return {
            'id': claim_id,
            'age': now - float(headers['x-timestamp']),
            'ttl': int(headers['x-delete-at']) - math.floor(now),
        }

    def get(self, queue, claim_id, project=None):
        now = timeutils.utcnow_ts(True)
        self._exists(queue, claim_id, project)

        container = utils._claim_container(queue, project)

        headers, claim_obj = self._client.get_object(container, claim_id)

        def g():
            for msg_id in jsonutils.loads(claim_obj):
                try:
                    headers, msg = self._message_ctrl._find_message(
                        queue, msg_id, project)
                except errors.MessageDoesNotExist:
                    continue
                else:
                    yield utils._message_to_json(msg_id, msg, headers, now)

        claim_meta = {
            'id': claim_id,
            'age': now - float(headers['x-timestamp']),
            'ttl': int(headers['x-delete-at']) - math.floor(now),
        }

        return claim_meta, g()

    def create(self, queue, metadata, project=None,
               limit=storage.DEFAULT_MESSAGES_PER_CLAIM):
        ttl = metadata['ttl']
        grace = metadata['grace']
        msg_ts = ttl + grace
        claim_id = uuidutils.generate_uuid()

        messages, marker = self._message_ctrl._list(
            queue, project, limit=limit, include_claimed=False)

        claimed = []
        for msg in messages:
            md5 = hashlib.md5()
            md5.update(
                jsonutils.dumps(
                    {'body': msg['body'], 'claim_id': None,
                     'ttl': msg['ttl']}))
            md5 = md5.hexdigest()
            msg_ttl = max(msg['ttl'], msg_ts)
            content = jsonutils.dumps(
                {'body': msg['body'], 'claim_id': claim_id, 'ttl': msg_ttl})
            try:
                self._client.put_object(
                    utils._message_container(queue, project),
                    msg['id'],
                    content,
                    content_type='application/json',
                    headers={'x-object-meta-clientid': msg['client_uuid'],
                             'if-match': md5,
                             'x-object-meta-claimid': claim_id,
                             'x-delete-after': msg_ttl})
            except swiftclient.ClientException as exc:
                if exc.http_status == 412:
                    continue
                raise
            else:
                msg['claim_id'] = claim_id
                msg['ttl'] = msg_ttl
                claimed.append(msg)

        utils._put_or_create_container(
            self._client,
            utils._claim_container(queue, project),
            claim_id,
            jsonutils.dumps([msg['id'] for msg in claimed]),
            content_type='application/json',
            headers={'x-delete-after': ttl}
        )

        return claim_id, claimed

    def update(self, queue, claim_id, metadata, project=None):
        container = utils._claim_container(queue, project)
        try:
            headers, obj = self._client.get_object(container, claim_id)
        except swiftclient.ClientException as exc:
            if exc.http_status == 404:
                raise errors.ClaimDoesNotExist(claim_id, queue, project)
            raise

        self._client.put_object(container, claim_id, obj,
                                content_type='application/json',
                                headers={'x-delete-after': metadata['ttl']})

    def delete(self, queue, claim_id, project=None):
        try:
            header, obj = self._client.get_object(
                utils._claim_container(queue, project),
                claim_id)
            for msg_id in jsonutils.loads(obj):
                try:
                    headers, msg = self._message_ctrl._find_message(
                        queue, msg_id, project)
                except errors.MessageDoesNotExist:
                    continue
                md5 = hashlib.md5()
                md5.update(msg)
                md5 = md5.hexdigest()
                msg = jsonutils.loads(msg)
                content = jsonutils.dumps(
                    {'body': msg['body'], 'claim_id': None, 'ttl': msg['ttl']})
                client_id = headers['x-object-meta-clientid']
                self._client.put_object(
                    utils._message_container(queue, project),
                    msg_id,
                    content,
                    content_type='application/json',
                    headers={'x-object-meta-clientid': client_id,
                             'if-match': md5,
                             'x-delete-at': headers['x-delete-at']})

            self._client.delete_object(
                utils._claim_container(queue, project),
                claim_id)
        except swiftclient.ClientException as exc:
            if exc.http_status != 404:
                raise

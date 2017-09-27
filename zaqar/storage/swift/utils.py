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

from oslo_serialization import jsonutils
from oslo_utils import timeutils
import swiftclient


def _message_container(queue, project=None):
    return "zaqar_message:%s:%s" % (queue, project)


def _claim_container(queue=None, project=None):
    return "zaqar_claim:%s:%s" % (queue, project)


def _subscription_container(queue, project=None):
    return "zaqar_subscription:%s:%s" % (queue, project)


def _subscriber_container(queue, project=None):
    return "zaqar_subscriber:%s:%s" % (queue, project)


def _put_or_create_container(client, *args, **kwargs):
    """PUT a swift object to a container that may not exist

    Takes the exact arguments of swiftclient.put_object but will
    autocreate a container that doesn't exist
    """
    try:
        client.put_object(*args, **kwargs)
    except swiftclient.ClientException as e:
        if e.http_status == 404:
            # Because of lazy creation, the container may be used by different
            # clients and cause cache problem. Retrying object creation a few
            # times should fix this.
            for i in range(5):
                client.put_container(args[0])
                try:
                    client.put_object(*args, **kwargs)
                except swiftclient.ClientException as ex:
                    if ex.http_status != 404:
                        raise
                else:
                    break
            else:
                # If we got there, we ignored the 5th exception, so the
                # exception context will be set.
                raise
        else:
            raise


def _message_to_json(message_id, msg, headers, now):
    msg = jsonutils.loads(msg)

    return {
        'id': message_id,
        'age': now - float(headers['x-timestamp']),
        'ttl': msg['ttl'],
        'body': msg['body'],
        'claim_id': msg['claim_id'],
        'claim_count': msg.get('claim_count', 0)
    }


def _subscription_to_json(sub, headers):
    sub = jsonutils.loads(sub)
    now = timeutils.utcnow_ts(True)
    return {'id': sub['id'],
            'age': now - float(headers['x-timestamp']),
            'source': sub['source'],
            'subscriber': sub['subscriber'],
            'ttl': sub['ttl'],
            'options': sub['options'],
            'confirmed': sub['confirmed']}


def _filter_messages(messages, filters, marker, get_object, list_objects,
                     limit):
    """Create a filtering iterator over a list of messages.

    The function accepts a list of filters to be filtered
    before the the message can be included as a part of the reply.
    """
    now = timeutils.utcnow_ts(True)

    for msg in messages:
        if msg is None:
            continue

        marker['next'] = msg['name']
        try:
            headers, obj = get_object(msg['name'])
        except swiftclient.ClientException as exc:
            if exc.http_status == 404:
                continue
            raise
        obj = jsonutils.loads(obj)
        for should_skip in filters:
            if should_skip(obj, headers):
                break
        else:
            limit -= 1
            yield {
                'id': marker['next'],
                'ttl': obj['ttl'],
                'client_uuid': headers['x-object-meta-clientid'],
                'body': obj['body'],
                'age': now - float(headers['x-timestamp']),
                'claim_id': obj['claim_id'],
                'claim_count': obj.get('claim_count', 0),
            }
            if limit <= 0:
                break
    if limit > 0 and marker:
        # We haven't reached the limit, let's try to get some more messages
        _, objects = list_objects(marker=marker['next'])
        if not objects:
            return
        for msg in _filter_messages(objects, filters, marker, get_object,
                                    list_objects, limit):
            yield msg


class SubscriptionListCursor(object):

    def __init__(self, objects, marker_next, get_object):
        self.objects = iter(objects)
        self.marker_next = marker_next
        self.get_object = get_object

    def __iter__(self):
        return self

    def next(self):
        while True:
            curr = next(self.objects)
            self.marker_next['next'] = curr['name']
            try:
                headers, sub = self.get_object(curr['name'])
            except swiftclient.ClientException as exc:
                if exc.http_status == 404:
                    continue
                raise
            return _subscription_to_json(sub, headers)

    def __next__(self):
        return self.next()

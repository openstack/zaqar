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

from marconi.queues.storage import errors


UNIX_EPOCH_AS_JULIAN_SEC = 2440587.5 * 86400.0


class NoResult(Exception):
    pass


def get_qid(driver, queue, project):
    try:
        return driver.get('''
            select id from Queues
             where project = ? and name = ?''', project, queue)[0]

    except NoResult:
        raise errors.QueueDoesNotExist(queue, project)


# The utilities below make the database IDs opaque to the users
# of Marconi API.  The only purpose is to advise the users NOT to
# make assumptions on the implementation of and/or relationship
# between the message IDs, the markers, and claim IDs.
#
# The magic numbers are arbitrarily picked; the numbers themselves
# come with no special functionalities.

def msgid_encode(id):
    return hex(id ^ 0x5c693a53)[2:]


def msgid_decode(id):
    try:
        return int(id, 16) ^ 0x5c693a53

    except ValueError:
        return None


def marker_encode(id):
    return oct(id ^ 0x3c96a355)[1:]


def marker_decode(id):
    try:
        return int(id, 8) ^ 0x3c96a355

    except ValueError:
        return None


def cid_encode(id):
    return hex(id ^ 0x63c9a59c)[2:]


def cid_decode(id):
    try:
        return int(id, 16) ^ 0x63c9a59c

    except ValueError:
        return None


def julian_to_unix(julian_sec):
    """Converts Julian timestamp, in seconds, to a UNIX timestamp."""
    return int(round(julian_sec - UNIX_EPOCH_AS_JULIAN_SEC))


def stat_message(message):
    """Creates a stat document based on a message."""
    return {
        'id': message['id'],
        'age': message['age'],
        'created': message['created'],
    }

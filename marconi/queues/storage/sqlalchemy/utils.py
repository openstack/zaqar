# Copyright (c) 2014 Red Hat, Inc.
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

import functools

import sqlalchemy as sa
from sqlalchemy import exc
from sqlalchemy.sql import func as sfunc

from marconi.openstack.common import log as logging
from marconi.queues.storage import errors
from marconi.queues.storage.sqlalchemy import tables


LOG = logging.getLogger(__name__)
UNIX_EPOCH_AS_JULIAN_SEC = 2440587.5 * 86400.0


def raises_conn_error(func):
    """Handles sqlalchemy DisconnectionError

    When sqlalchemy detects a disconnect from the database server, it
    retries a number of times. After failing that number of times, it
    will convert the internal DisconnectionError into an
    InvalidRequestError. This decorator handles that error.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exc.InvalidRequestError as ex:
            LOG.exception(ex)
            raise errors.ConnectionError()

    return wrapper


class NoResult(Exception):
    pass


def get_qid(driver, queue, project):
    sel = sa.sql.select([tables.Queues.c.id], sa.and_(
                        tables.Queues.c.project == project,
                        tables.Queues.c.name == queue))
    try:
        return driver.get(sel)[0]
    except NoResult:
        raise errors.QueueDoesNotExist(queue, project)


def get_age(created):
    return sfunc.now() - created

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

# Copyright (c) 2013 Red Hat, Inc.
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

from bson import errors as berrors
from bson import objectid

from marconi.openstack.common import timeutils


def to_oid(obj):
    """
    Creates a new ObjectId based on the input
    and raises ValueError whenever a TypeError
    or InvalidId error is raised by the ObjectID
    class.

    :param obj: Anything that can be passed as an
        input to `objectid.ObjectId`
    """
    try:
        return objectid.ObjectId(obj)
    except (TypeError, berrors.InvalidId):
        msg = _("Wrong id %s") % obj
        raise ValueError(msg)


def oid_utc(oid):
    """
    Creates a non-tz-aware datetime based on
    the incoming objectid's datetime information.
    """
    try:
        return timeutils.normalize_time(oid.generation_time)
    except AttributeError:
        raise TypeError(_("Expected ObjectId and got %s") % type(oid))


class HookedCursor(object):

    def __init__(self, cursor, denormalizer):
        self.cursor = cursor
        self.denormalizer = denormalizer

    def __getattr__(self, attr):
        return getattr(self.cursor, attr)

    def __iter__(self):
        return self

    def __len__(self):
        return self.cursor.count(True)

    def next(self):
        item = self.cursor.next()
        return self.denormalizer(item)

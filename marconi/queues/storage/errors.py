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


class ConnectionError(Exception):
    """Raised when the connection with the back-end
    was lost.
    """


class DoesNotExist(Exception):
    """Resource does not exist."""


class NotPermitted(Exception):
    """Operation not permitted."""


class Conflict(Exception):
    """Resource could not be created due to a conflict
    with an existing resource.
    """


class MessageConflict(Conflict):

    def __init__(self, queue, project, message_ids):
        """Initializes the error with contextual information.

        :param queue: name of the queue to which the message was posted
        :param project: name of the project to which the queue belongs
        :param message_ids: list of IDs for messages successfully
            posted. Note that these must be in the same order as the
            list of messages originally submitted to be enqueued.
        """
        msg = (u'Message could not be enqueued due to a conflict '
               u'with another message that is already in '
               u'queue %(queue)s for project %(project)s' %
               dict(queue=queue, project=project))

        super(MessageConflict, self).__init__(msg)

        self._succeeded_ids = message_ids

    @property
    def succeeded_ids(self):
        return self._succeeded_ids


class QueueDoesNotExist(DoesNotExist):

    def __init__(self, name, project):
        msg = (u'Queue %(name)s does not exist for project %(project)s' %
               dict(name=name, project=project))
        super(QueueDoesNotExist, self).__init__(msg)


class QueueIsEmpty(Exception):

    def __init__(self, name, project):
        msg = (u'Queue %(name)s in project %(project)s is empty' %
               dict(name=name, project=project))
        super(QueueIsEmpty, self).__init__(msg)


class MessageDoesNotExist(DoesNotExist):

    def __init__(self, mid, queue, project):
        msg = (u'Message %(mid)s does not exist in '
               u'queue %(queue)s for project %(project)s' %
               dict(mid=mid, queue=queue, project=project))
        super(MessageDoesNotExist, self).__init__(msg)


class MessageIsClaimed(NotPermitted):

    def __init__(self, mid):
        msg = (u'Message %(mid)s is claimed' % dict(mid=mid))
        super(MessageIsClaimed, self).__init__(msg)


class ClaimDoesNotExist(DoesNotExist):

    def __init__(self, cid, queue, project):
        msg = (u'Claim %(cid)s does not exist in '
               u'queue %(queue)s for project %(project)s' %
               dict(cid=cid, queue=queue, project=project))
        super(ClaimDoesNotExist, self).__init__(msg)


class QueueNotMapped(DoesNotExist):

    def __init__(self, queue, project):
        msg = (u'No shard found for '
               u'queue %(queue)s for project %(project)s' %
               dict(queue=queue, project=project))
        super(QueueNotMapped, self).__init__(msg)


class MessageIsClaimedBy(NotPermitted):

    def __init__(self, mid, cid):
        msg = (u'Message %(mid)s is not claimed by %(cid)s' %
               dict(cid=cid, mid=mid))
        super(MessageIsClaimedBy, self).__init__(msg)


class ShardDoesNotExist(DoesNotExist):

    def __init__(self, shard):
        msg = u'Shard {0} does not exists'.format(shard)
        super(ShardDoesNotExist, self).__init__(msg)


class NoShardFound(Exception):

    def __init__(self):
        msg = u'No shards registered'
        super(NoShardFound, self).__init__(msg)

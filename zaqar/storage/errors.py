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


class ExceptionBase(Exception):

    msg_format = ''

    def __init__(self, **kwargs):
        msg = self.msg_format.format(**kwargs)
        super(ExceptionBase, self).__init__(msg)


class ConnectionError(ExceptionBase):
    """Raised when the connection with the back-end was lost."""


class DoesNotExist(ExceptionBase):
    """Resource does not exist."""


class NotPermitted(ExceptionBase):
    """Operation not permitted."""


class Conflict(ExceptionBase):
    """Resource could not be created due to a conflict."""


class MessageConflict(Conflict):

    msg_format = (u'Message could not be enqueued due to a conflict '
                  u'with one or more other messages that are already in '
                  u'queue {queue} for project {project}')

    def __init__(self, queue, project):
        """Initializes the error with contextual information.

        :param queue: name of the queue to which the message was posted

        :param project: name of the project to which the queue belongs
        """

        super(MessageConflict, self).__init__(queue=queue, project=project)


class ClaimConflict(Conflict):

    msg_format = (u'Messages could not be claimed due to a conflict '
                  u'with another parallel claim that is already in '
                  u'queue {queue} for project {project}')

    def __init__(self, queue, project):
        """Initializes the error with contextual information.

        :param queue: name of the queue to which the message was posted
        :param project: name of the project to which the queue belongs
        """

        super(ClaimConflict, self).__init__(queue=queue, project=project)


class QueueDoesNotExist(DoesNotExist):

    msg_format = u'Queue {name} does not exist for project {project}'

    def __init__(self, name, project):
        super(QueueDoesNotExist, self).__init__(name=name, project=project)


class QueueIsEmpty(ExceptionBase):

    msg_format = u'Queue {name} in project {project} is empty'

    def __init__(self, name, project):
        super(QueueIsEmpty, self).__init__(name=name, project=project)


class MessageDoesNotExist(DoesNotExist):

    msg_format = (u'Message {mid} does not exist in '
                  u'queue {queue} for project {project}')

    def __init__(self, mid, queue, project):
        super(MessageDoesNotExist, self).__init__(mid=mid, queue=queue,
                                                  project=project)


class ClaimDoesNotExist(DoesNotExist):

    msg_format = (u'Claim {cid} does not exist in '
                  u'queue {queue} for project {project}')

    def __init__(self, cid, queue, project):
        super(ClaimDoesNotExist, self).__init__(cid=cid, queue=queue,
                                                project=project)


class MessageIsClaimed(NotPermitted):

    msg_format = u'Message {mid} is claimed'

    def __init__(self, mid):
        super(MessageIsClaimed, self).__init__(mid=mid)


class MessageNotClaimed(NotPermitted):

    msg_format = u'Message {mid} is no longer claimed'

    def __init__(self, mid):
        super(MessageNotClaimed, self).__init__(mid=mid)


class MessageNotClaimedBy(NotPermitted):

    msg_format = u'Message {mid} is not claimed by {cid}'

    def __init__(self, mid, cid):
        super(MessageNotClaimedBy, self).__init__(cid=cid, mid=mid)


class QueueNotMapped(DoesNotExist):

    msg_format = (u'No pool found for '
                  u'queue {queue} for project {project}')

    def __init__(self, queue, project):
        super(QueueNotMapped, self).__init__(queue=queue, project=project)


class PoolDoesNotExist(DoesNotExist):

    msg_format = u'Pool {pool} does not exist'

    def __init__(self, pool):
        super(PoolDoesNotExist, self).__init__(pool=pool)


class PoolGroupDoesNotExist(DoesNotExist):

    msg_format = u'Pool group {pool_group} does not exist'

    def __init__(self, pool_group):
        super(PoolGroupDoesNotExist, self).__init__(pool_group=pool_group)


class FlavorDoesNotExist(DoesNotExist):

    msg_format = u'Flavor {flavor} does not exist'

    def __init__(self, flavor):
        super(FlavorDoesNotExist, self).__init__(flavor=flavor)


class NoPoolFound(ExceptionBase):

    msg_format = u'No pools registered'

    def __init__(self):
        super(NoPoolFound, self).__init__()


class PoolInUseByFlavor(NotPermitted):

    msg_format = u'Pool {pid} is in use by flavor {fid}'

    def __init__(self, pid, fid):
        super(PoolInUseByFlavor, self).__init__(pid=pid, fid=fid)
        self._flavor = fid

    @property
    def flavor(self):
        return self._flavor


class SubscriptionDoesNotExist(DoesNotExist):

    msg_format = u'Subscription {subscription_id} does not exist'

    def __init__(self, subscription_id):
        super(SubscriptionDoesNotExist,
              self).__init__(subscription_id=subscription_id)


class PoolCapabilitiesMismatch(ExceptionBase):

    msg_format = (u'The pool being added does not '
                  u'support the minimum set of capabilities')


class PoolAlreadyExists(Conflict):

    msg_format = u'The database URI is in use by another pool.'


class SubscriptionAlreadyExists(Conflict):

    msg_format = (u'Such subscription already exists. Subscriptions '
                  u'are unique by project + queue + subscriber URI.')

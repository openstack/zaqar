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


class DoesNotExist(Exception):
    pass


class NotPermitted(Exception):
    pass


class QueueDoesNotExist(DoesNotExist):

    def __init__(self, name, project):
        msg = (_("Queue %(name)s does not exist for project %(project)s") %
               dict(name=name, project=project))
        super(QueueDoesNotExist, self).__init__(msg)


class MessageDoesNotExist(DoesNotExist):

    def __init__(self, mid, queue, project):
        msg = (_("Message %(mid)s does not exist in "
                 "queue %(queue)s of project %(project)s") %
               dict(mid=mid, queue=queue, project=project))
        super(MessageDoesNotExist, self).__init__(msg)


class ClaimDoesNotExist(DoesNotExist):

    def __init__(self, cid, queue, project):
        msg = (_("Claim %(cid)s does not exist in "
                 "queue %(queue)s of project %(project)s") %
               dict(cid=cid, queue=queue, project=project))
        super(ClaimDoesNotExist, self).__init__(msg)


class ClaimNotPermitted(NotPermitted):

    def __init__(self, mid, cid):
        msg = (_("Message %(mid)s is not claimed by %(cid)s") %
               dict(cid=cid, mid=mid))
        super(ClaimNotPermitted, self).__init__(msg)

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

    def __init__(self, name, tenant):
        msg = (_("Queue %(name)s does not exist for tenant %(tenant)s") %
               dict(name=name, tenant=tenant))
        super(QueueDoesNotExist, self).__init__(msg)


class MessageDoesNotExist(DoesNotExist):

    def __init__(self, mid, queue, tenant):
        msg = (_("Message %(mid)s does not exist in "
                 "queue %(queue)s of tenant %(tenant)s") %
               dict(mid=mid, queue=queue, tenant=tenant))
        super(MessageDoesNotExist, self).__init__(msg)


class ClaimDoesNotExist(DoesNotExist):

    def __init__(self, cid, queue, tenant):
        msg = (_("Claim %(cid)s does not exist in "
                 "queue %(queue)s of tenant %(tenant)s") %
               dict(cid=cid, queue=queue, tenant=tenant))
        super(ClaimDoesNotExist, self).__init__(msg)

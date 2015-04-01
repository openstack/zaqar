# Copyright (c) 2015 Red Hat, Inc.
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

from zaqar.tests.unit.transport.websocket import v1_1

# --------------------------------------------------------------------------
# Identical or just minor variations across versions
# --------------------------------------------------------------------------


# TODO(kgriffs): Having to list a separate test for each backend is
# sort of a pain; is there a better way?
class TestQueueLifecycleMongoDB(v1_1.TestQueueLifecycleMongoDB):
    pass

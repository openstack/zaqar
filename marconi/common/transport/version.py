# Copyright (c) 2013 Rackspace Hosting, Inc.
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

"""version: version information for the transport API."""


def info():
    """Returns the API version as a tuple.

    :rtype: (int, int)
    """
    return (1, 0)


def path():
    """Returns the API version as /v{version}.

    :returns: /v{version}
    :rtype: text
    """
    return '/v{0}'.format(info()[0])

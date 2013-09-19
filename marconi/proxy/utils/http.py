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
"""http: utilities for handling HTTP details."""
import falcon


METHODS = (
    'get', 'put', 'head', 'delete', 'post',
    'patch', 'options'
)


_code_map = dict((int(v.split()[0]), v)
                 for k, v in falcon.status_codes.__dict__.items()
                 if k.startswith('HTTP_'))


def status(code):
    """Maps an integer HTTP status code to a friendly HTTP status message

    :raises: KeyError for an unknown HTTP status code
    """
    return _code_map[code]

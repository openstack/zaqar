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
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import simplejson as json
except ImportError:
    import json


class MalformedJSON(Exception):
    pass


def read_json(stream):
    """
    Like json.load, but raises an exception upon failure.

    :param stream: a file-like object
    """
    try:
        return json.load(stream)

    except Exception:
        raise MalformedJSON


def to_json(obj):
    """
    Like json.dumps, but outputs a UTF-8 encoded string.

    :param obj: a JSON-serializable object
    """
    return json.dumps(obj, ensure_ascii=False)

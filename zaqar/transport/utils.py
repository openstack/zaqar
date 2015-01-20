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

import json

from oslo_utils import encodeutils


class MalformedJSON(ValueError):
    """JSON string is not valid."""
    pass


class OverflowedJSONInteger(OverflowError):
    """JSON integer is too large."""
    pass


def _json_int(s):
    """Parse a string as a base 10 64-bit signed integer."""
    i = int(s)
    if not (int(-2 ** 63) <= i <= int(2 ** 63 - 1)):
        raise OverflowedJSONInteger()

    return i


def read_json(stream, len):
    """Like json.load, but converts ValueError to MalformedJSON upon failure.

    :param stream: a file-like object
    :param len: the number of bytes to read from stream
    """
    try:
        content = encodeutils.safe_decode(stream.read(len), 'utf-8')
        return json.loads(content, parse_int=_json_int)
    except UnicodeDecodeError as ex:
        raise MalformedJSON(ex)
    except ValueError as ex:
        raise MalformedJSON(ex)


def to_json(obj):
    """Like json.dumps, but outputs a UTF-8 encoded string.

    :param obj: a JSON-serializable object
    """
    return json.dumps(obj, ensure_ascii=False)

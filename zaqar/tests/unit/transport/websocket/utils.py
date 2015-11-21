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

import functools
import json
import msgpack


def create_request(action, body, headers):
    return json.dumps({"action": action, "body": body, "headers": headers})


def create_binary_request(action, body, headers):
    return msgpack.packb({"action": action, "body": body, "headers": headers})


def get_pack_tools(binary=None):
    """Get serialization tools for testing websocket transport.

    :param bool binary: type of serialization tools.
    True: binary (MessagePack) tools.
    False: text (JSON) tools.
    :returns: set of serialization tools needed for testing websocket
    transport: (dumps, loads, create_request_function)
    :rtype: tuple
    """
    if binary is None:
        raise Exception("binary param is unspecified")
    if binary:
        dumps = msgpack.Packer(encoding='utf-8', use_bin_type=False).pack
        loads = functools.partial(msgpack.unpackb, encoding='utf-8')
        create_request_function = create_binary_request
    else:
        dumps = json.dumps
        loads = json.loads
        create_request_function = create_request
    return dumps, loads, create_request_function

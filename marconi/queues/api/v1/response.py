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

from marconi.common import api


class ResponseSchema(api.Api):

    """Define validation schema for json response."""

    def __init__(self, limits):
        self.limits = limits
        self.schema = {
            'message_get_many':
            {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "href": {
                            "type": "string",
                            "pattern": "^(/v1/queues/[a-zA-Z0-9_-]{1,64}"
                            "/messages/[a-zA-Z0-9_-]+)$"
                        },
                        "ttl": {
                            "type": "number",
                            "minimum": 1,
                            "maximum": self.limits.max_message_ttl
                        },
                        "age": {
                            "type": "number",
                            "minimum": 0
                        },
                        "body": {
                            "type": "object"
                        }
                    },
                    "required": ["href", "ttl", "age", "body"]
                },
                "minItems": 1,
                "maxItems": self.limits.max_messages_per_page
            }
        }

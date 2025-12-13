# Copyright 2011 OpenStack Foundation
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""RequestContext: context for requests that persist through all of zaqar."""

from oslo_context import context


class RequestContext(context.RequestContext):

    FROM_DICT_EXTRA_KEYS = ['client_id']

    def __init__(self, *, client_id=None, **kwargs):
        self.client_id = client_id
        super().__init__(**kwargs)

    def to_dict(self):
        values = super().to_dict()
        values.update({
            'client_id': self.client_id
        })
        return values

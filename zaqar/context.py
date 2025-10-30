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

    def __init__(self, project_id=None, client_id=None, overwrite=True,
                 auth_token=None, user_id=None, domain_id=None,
                 user_domain_id=None, project_domain_id=None, is_admin=False,
                 read_only=False, request_id=None, roles=None, **kwargs):
        super().__init__(
            auth_token=auth_token,
            user_id=user_id,
            project_id=project_id,
            domain_id=domain_id,
            user_domain_id=user_domain_id,
            project_domain_id=project_domain_id,
            is_admin=is_admin,
            read_only=read_only,
            show_deleted=False,
            request_id=request_id,
            roles=roles)
        self.client_id = client_id
        if overwrite or not hasattr(context._request_store, 'context'):
            self.update_store()

    def update_store(self):
        context._request_store.context = self

    def to_dict(self):
        ctx = super().to_dict()
        ctx.update({
            'project_id': self.project_id,
            'client_id': self.client_id
        })
        return ctx

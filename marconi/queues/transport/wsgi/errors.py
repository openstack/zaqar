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

import falcon


class HTTPServiceUnavailable(falcon.HTTPServiceUnavailable):
    """Wraps falcon.HTTPServiceUnavailable with Marconi messaging."""

    TITLE = _(u'Service temporarily unavailable')
    DESCRIPTION = _(u'Please try again in a few seconds.')

    def __init__(self, description, retry_after=30):
        description = description + ' ' + self.DESCRIPTION
        super(HTTPServiceUnavailable, self).__init__(
            self.TITLE, description, retry_after)


class HTTPBadRequestAPI(falcon.HTTPBadRequest):
    """Wraps falcon.HTTPBadRequest with a contextual title."""

    TITLE = _(u'Invalid API call')

    def __init__(self, description):
        super(HTTPBadRequestAPI, self).__init__(self.TITLE, description)


class HTTPBadRequestBody(falcon.HTTPBadRequest):
    """Wraps falcon.HTTPBadRequest with a contextual title."""

    TITLE = _(u'Invalid request body')

    def __init__(self, description):
        super(HTTPBadRequestBody, self).__init__(self.TITLE, description)


class HTTPDocumentTypeNotSupported(HTTPBadRequestBody):
    """Wraps HTTPBadRequestBody with a standard description."""

    DESCRIPTION = _(u'Document type not supported.')

    def __init__(self):
        super(HTTPDocumentTypeNotSupported, self).__init__(self.DESCRIPTION)

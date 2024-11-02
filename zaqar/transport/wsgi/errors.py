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

from zaqar.i18n import _


class HTTPServiceUnavailable(falcon.HTTPServiceUnavailable):
    """Wraps falcon.HTTPServiceUnavailable with Zaqar messaging."""

    TITLE = _('Service temporarily unavailable')
    DESCRIPTION = _('Please try again in a few seconds.')

    def __init__(self, description):
        description = description + ' ' + self.DESCRIPTION
        super(HTTPServiceUnavailable, self).__init__(
            title=self.TITLE, description=description)


class HTTPBadRequestAPI(falcon.HTTPBadRequest):
    """Wraps falcon.HTTPBadRequest with a contextual title."""

    TITLE = _('Invalid API request')

    def __init__(self, description):
        super(HTTPBadRequestAPI, self).__init__(
            title=self.TITLE, description=description)


class HTTPBadRequestBody(falcon.HTTPBadRequest):
    """Wraps falcon.HTTPBadRequest with a contextual title."""

    TITLE = _('Invalid request body')

    def __init__(self, description):
        super(HTTPBadRequestBody, self).__init__(
            title=self.TITLE, description=description)


class HTTPDocumentTypeNotSupported(HTTPBadRequestBody):
    """Wraps HTTPBadRequestBody with a standard description."""

    DESCRIPTION = _('Document type not supported.')

    def __init__(self):
        super(HTTPDocumentTypeNotSupported, self).__init__(self.DESCRIPTION)


class HTTPForbidden(falcon.HTTPForbidden):
    """Wraps falcon.HTTPForbidden with a contextual title."""

    TITLE = _('Not authorized')
    DESCRIPTION = _('You are not authorized to complete this action.')

    def __init__(self):
        super(HTTPForbidden, self).__init__(
            title=self.TITLE, description=self.DESCRIPTION)


class HTTPConflict(falcon.HTTPConflict):
    """Wraps falcon.HTTPConflict with contextual title."""

    TITLE = _('Resource conflict')

    def __init__(self, description, **kwargs):
        super(HTTPConflict, self).__init__(
            title=self.TITLE, description=description, **kwargs)


class HTTPNotFound(falcon.HTTPNotFound):
    """Wraps falcon.HTTPConflict with contextual title."""

    TITLE = _('Not found')

    def __init__(self, description):
        super(HTTPNotFound, self).__init__(
            title=self.TITLE, description=description)


class HTTPUnsupportedMediaType(falcon.HTTPUnsupportedMediaType):
    """Wraps falcon.HTTPUnsupportedMediaType with contextual title."""

    def __init__(self, description):
        super(HTTPUnsupportedMediaType, self).__init__(
            description=description)

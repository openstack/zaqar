# Copyright 2015 Red Hat, Inc.
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

import os

from oslo_log import log as logging
import six

from zaqar.common import decorators
from zaqar.common import urls
from zaqar.transport import acl
from zaqar.transport import utils
from zaqar.transport.wsgi import errors as wsgi_errors
from zaqar.transport.wsgi import utils as wsgi_utils

LOG = logging.getLogger(__name__)

_KNOWN_KEYS = {'methods', 'expires', 'paths'}

_VALID_PATHS = {'messages', 'subscriptions', 'claims'}


class Resource(object):

    __slots__ = ('_driver', '_conf')

    def __init__(self, driver):
        self._driver = driver
        self._conf = driver._conf

    @decorators.TransportLog("Queues share item")
    @acl.enforce("queues:share")
    def on_post(self, req, resp, project_id, queue_name):
        LOG.debug(u'Pre-Signed URL Creation for queue: %(queue)s, '
                  u'project: %(project)s',
                  {'queue': queue_name, 'project': project_id})

        try:
            document = wsgi_utils.deserialize(req.stream, req.content_length)
        except ValueError as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        diff = set(document.keys()) - _KNOWN_KEYS
        if diff:
            msg = six.text_type('Unknown keys: %s' % diff)
            raise wsgi_errors.HTTPBadRequestAPI(msg)

        key = self._conf.signed_url.secret_key
        paths = document.pop('paths', None)
        if not paths:
            paths = [os.path.join(req.path[:-6], 'messages')]
        else:
            diff = set(paths) - _VALID_PATHS
            if diff:
                msg = six.text_type('Invalid paths: %s' % diff)
                raise wsgi_errors.HTTPBadRequestAPI(msg)
            paths = [os.path.join(req.path[:-6], path) for path in paths]

        try:
            data = urls.create_signed_url(key, paths,
                                          project=project_id,
                                          **document)
        except ValueError as err:
            raise wsgi_errors.HTTPBadRequestAPI(str(err))

        resp.body = utils.to_json(data)

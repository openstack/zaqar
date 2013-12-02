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

"""wsgi transport helpers."""

import falcon

import marconi.openstack.common.log as logging
from marconi.queues.transport import validation


LOG = logging.getLogger(__name__)


def extract_project_id(req, resp, params):
    """Adds `project_id` to the list of params for all responders

    Meant to be used as a `before` hook.

    :param req: request sent
    :type req: falcon.request.Request
    :param resp: response object to return
    :type resp: falcon.response.Response
    :param params: additional parameters passed to responders
    :type params: dict
    :rtype: None
    """
    params['project_id'] = req.get_header('X-PROJECT-ID')
    if params['project_id'] == "":
        raise falcon.HTTPBadRequest('Empty project header not allowed',
                                    _(u'''
X-PROJECT-ID cannot be an empty string. Specify the right header X-PROJECT-ID
and retry.'''))


def validate_queue_identification(validate, req, resp, params):
    """Hook for validating the queue name and project id in requests.

    The queue name validation is short-circuited if 'queue_name' does
    not exist in `params`.

    This hook depends on the `get_project` hook, which must be
    installed upstream.


    :param validate: A validator function that will
        be used to check the queue name against configured
        limits. functools.partial or a closure must be used to
        set this first arg, and expose the remaining ones as
        a Falcon hook interface.
    :param req: Falcon request object
    :param resp: Falcon response object
    :param params: Responder params dict
    """

    try:
        validate(params['queue_name'],
                 params['project_id'])
    except KeyError:
        # NOTE(kgriffs): queue_name not in params, so nothing to do
        pass
    except validation.ValidationFailed:
        project = params['project_id']
        queue = params['queue_name'].decode('utf-8', 'replace')

        LOG.warn(_(u'Invalid queue name "%(queue)s" submitted for '
                   u'project: %(project)s'),
                 {'queue': queue, 'project': project})

        raise falcon.HTTPBadRequest(_(u'Invalid queue identification'),
                                    _(u'The format of the submitted queue '
                                      u'name or project id is not valid.'))


def require_accepts_json(req, resp, params):
    """Raises an exception if the request does not accept JSON

    Meant to be used as a `before` hook.

    :param req: request sent
    :type req: falcon.request.Request
    :param resp: response object to return
    :type resp: falcon.response.Response
    :param params: additional parameters passed to responders
    :type params: dict
    :rtype: None
    :raises: falcon.HTTPNotAcceptable
    """
    if not req.client_accepts('application/json'):
        raise falcon.HTTPNotAcceptable(
            u'''
Endpoint only serves `application/json`; specify client-side
media type support with the "Accept" header.''',
            href=u'http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html',
            href_text=u'14.1 Accept, Hypertext Transfer Protocol -- HTTP/1.1')

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

import re
from stevedore import driver
import uuid

import falcon
from oslo_log import log as logging

from zaqar.common import urls
from zaqar import context
from zaqar.i18n import _
from zaqar.transport import validation


LOG = logging.getLogger(__name__)


def verify_pre_signed_url(key, req, resp, params):
    headers = req.headers
    project = headers.get('X-PROJECT-ID')
    expires = headers.get('URL-EXPIRES')
    methods = headers.get('URL-METHODS', '').split(',')
    paths = headers.get('URL-PATHS', '').split(',')
    signature = headers.get('URL-SIGNATURE')

    if not signature:
        return

    if req.method not in methods:
        raise falcon.HTTPNotFound()

    # Support to query single resource with pre-signed url
    if not any([p for p in paths if re.search(p, req.path)]):
        raise falcon.HTTPNotFound()

    try:
        verified = urls.verify_signed_headers_data(key, paths,
                                                   project=project,
                                                   methods=methods,
                                                   expires=expires,
                                                   signature=signature)
    except ValueError:
        raise falcon.HTTPNotFound()

    if not verified:
        raise falcon.HTTPNotFound()


def get_client_uuid(req):
    """Read a required Client-ID from a request.

    :param req: A falcon.Request object
    :returns: A UUID object or A string of client id
    """

    try:
        return uuid.UUID(req.get_header('Client-ID', required=True))
    except ValueError:
        return req.get_header('Client-ID', required=True)


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
    api_version_string = req.path.split('/')[1]
    params['project_id'] = req.get_header('X-PROJECT-ID')
    if not api_version_string:
        # NOTE(jaosorior): The versions resource is public and shouldn't need
        # a check for the project-id.
        return
    if params['project_id'] == "":
        raise falcon.HTTPBadRequest(
            title='Empty project header not allowed',
            description=_('X-PROJECT-ID cannot be an empty string. Specify '
                          'the right header X-PROJECT-ID and retry.'))

    if not params['project_id']:
        raise falcon.HTTPBadRequest(
            title='Project-Id Missing',
            description=_('The header X-PROJECT-ID was missing'))


def require_client_id(validate, req, resp, params):
    """Makes sure the header `Client-ID` is present in the request

    Use as a before hook.

    :param validate: A validator function that will
        be used to check the format of client id against configured
        limits.
    :param req: request sent
    :type req: falcon.request.Request
    :param resp: response object to return
    :type resp: falcon.response.Response
    :param params: additional parameters passed to responders
    :type params: dict
    :rtype: None
    """
    api_version_string = req.path.split('/')[1]
    if not api_version_string:
        # we don't insist on a Client-ID for the versions resource
        return

    try:
        validate(req.get_header('Client-ID', required=True))
    except ValueError:
        description = _('Malformed hexadecimal UUID.')
        raise falcon.HTTPBadRequest(
            title='Wrong UUID value', description=description)
    except validation.ValidationFailed as ex:
        raise falcon.HTTPBadRequest(title=str(ex))


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
        queue = params['queue_name']

        LOG.debug('Invalid queue name "%(queue)s" submitted for '
                  'project: %(project)s',
                  {'queue': queue, 'project': project})

        raise falcon.HTTPBadRequest(
            title=_('Invalid queue identification'),
            description=_('The format of the submitted queue '
                          'name or project id is not valid.'))


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
    :raises HTTPNotAcceptable: if the request does not accept JSON
    """
    if not req.client_accepts('application/json'):
        raise falcon.HTTPNotAcceptable(
            description='Endpoint only serves `application/json`; '
                        'specify client-side media type support with '
                        'the "Accept" header.',
            href='http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html',
            href_text='14.1 Accept, Hypertext Transfer Protocol -- HTTP/1.1')


def require_content_type_be_non_urlencoded(req, resp, params):
    """Raises an exception on "x-www-form-urlencoded" content type of request.

    If request has body and "Content-Type" header has
    "application/x-www-form-urlencoded" value (case-insensitive), this function
    raises falcon.HTTPBadRequest exception.

    This strange function exists only to prevent bug/1547100 in a backward
    compatible way.

    Meant to be used as a `before` hook.

    :param req: request sent
    :type req: falcon.request.Request
    :param resp: response object to return
    :type resp: falcon.response.Response
    :param params: additional parameters passed to responders
    :type params: dict
    :rtype: None
    :raises HTTPBadRequest: if request has body and "Content-Type" header has
        "application/x-www-form-urlencoded" value
    """
    if req.content_length is None:
        return
    if req.content_type and (req.content_type.lower() ==
                             'application/x-www-form-urlencoded'):
        title = _('Invalid Content-Type')
        description = _('Endpoint does not accept '
                        '`application/x-www-form-urlencoded` content; '
                        'currently supported media type is '
                        '`application/json`; specify proper client-side '
                        'media type with the "Content-Type" header.')
        raise falcon.HTTPBadRequest(title=title, description=description)


def inject_context(req, resp, params):
    """Inject context value into request environment.

    :param req: request sent
    :type req: falcon.request.Request
    :param resp: response object
    :type resp: falcon.response.Response
    :param params: additional parameters passed to responders
    :type params: dict
    :rtype: None

    """
    client_id = req.get_header('Client-ID')
    request_id = req.headers.get('X-Openstack-Request-ID')
    auth_token = req.headers.get('X-AUTH-TOKEN')
    project_id = params.get('project_id')
    user_id = req.headers.get('X-USER-ID')
    domain_id = req.headers.get('X-DOMAIN-ID')
    project_domain_id = req.headers.get('X-PROJECT-DOMAIN-ID')
    user_domain_id = req.headers.get('X-USER-DOMAIN-ID')
    roles = req.headers.get('X-ROLES')
    roles = roles and roles.split(',') or []

    ctxt = context.RequestContext(project_id=project_id,
                                  client_id=client_id,
                                  request_id=request_id,
                                  auth_token=auth_token,
                                  user_id=user_id,
                                  roles=roles,
                                  domain_id=domain_id,
                                  project_domain_id=project_domain_id,
                                  user_domain_id=user_domain_id)
    req.env['zaqar.context'] = ctxt


def validate_topic_identification(validate, req, resp, params):
    """Hook for validating the topic name and project id in requests.

    The queue name validation is short-circuited if 'topic_name' does
    not exist in `params`.

    This hook depends on the `get_project` hook, which must be
    installed upstream.


    :param validate: A validator function that will
        be used to check the topic name against configured
        limits. functools.partial or a closure must be used to
        set this first arg, and expose the remaining ones as
        a Falcon hook interface.
    :param req: Falcon request object
    :param resp: Falcon response object
    :param params: Responder params dict
    """

    try:
        validate(params['topic_name'],
                 params['project_id'])
    except KeyError:
        # NOTE(kgriffs): topic not in params, so nothing to do
        pass
    except validation.ValidationFailed:
        project = params['project_id']
        queue = params['topic_name']

        LOG.debug('Invalid topic name "%(topic)s" submitted for '
                  'project: %(project)s',
                  {'topic': queue, 'project': project})

        raise falcon.HTTPBadRequest(
            title=_('Invalid topic identification'),
            description=_('The format of the submitted topic '
                          'name or project id is not valid.'))


def verify_extra_spec(req, resp, params):
    """Extract `extra_spec` from request and verify it.

    Meant to be used as a `before` hook.

    :param req: request sent
    :type req: falcon.request.Request
    :param resp: response object to return
    :type resp: falcon.response.Response
    :param params: additional parameters passed to responders
    :type params: dict
    :rtype: None
    """
    extra_spec = req.get_header('EXTRA-SPEC')
    if not extra_spec:
        return

    if extra_spec == "":
        raise falcon.HTTPBadRequest(
            title='Empty extra spec not allowed',
            description=_('Extra spec cannot be an empty '
                          'if specify the header.'))
    extra_spec_schema = extra_spec.split(':')[0]
    if extra_spec_schema:
        mgr = driver.DriverManager('zaqar.extraspec.tasks', extra_spec_schema,
                                   invoke_on_load=True)
        mgr.driver.execute(extra_spec)

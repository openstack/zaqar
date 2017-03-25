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
import uuid

from oslo_log import log as logging
from oslo_utils import strutils

import zaqar.common.api.errors as api_errors
import zaqar.common.api.response as response
from zaqar.i18n import _

LOG = logging.getLogger(__name__)


def sanitize(document, spec=None, doctype=dict):
    """Validates a document and drops undesired fields.

    :param document: A dict to verify according to `spec`.
    :param spec: (Default None) Iterable describing expected fields,
        yielding tuples with the form of:

            (field_name, value_type, default_value)

        Note that value_type may either be a Python type, or the
        special string '*' to accept any type. default_value is the
        default to give the field if it is missing, or None to require
        that the field be present.

        If spec is None, the incoming documents will not be validated.
    :param doctype: type of document to expect; must be either
        JSONObject or JSONArray.
    :raises DocumentTypeNotSupported: if document type is not supported
    :raises TypeError: if document type is neither a JSONObject
        nor JSONArray
    :returns: A sanitized, filtered version of the document. If the
        document is a list of objects, each object will be filtered
        and returned in a new list. If, on the other hand, the document
        is expected to contain a single object, that object's fields will
        be filtered and the resulting object will be returned.
    """

    if doctype is dict:
        if not isinstance(document, dict):
            raise api_errors.DocumentTypeNotSupported()

        return document if spec is None else filter_fields(document, spec)

    if doctype is list:
        if not isinstance(document, list):
            raise api_errors.DocumentTypeNotSupported()

        if spec is None:
            return document

        return [filter_fields(obj, spec) for obj in document]

    raise TypeError(_(u'Doctype must be either a JSONObject or JSONArray'))


def filter_fields(document, spec):
    """Validates and retrieves typed fields from a single document.

    Sanitizes a dict-like document by checking it against a
    list of field spec, and returning only those fields
    specified.

    :param document: dict-like object
    :param spec: iterable describing expected fields, yielding
        tuples with the form of: (field_name, value_type). Note that
        value_type may either be a Python type, or the special
        string '*' to accept any type.
    :raises BadRequest: if any field is missing or not an
        instance of the specified type
    :returns: A filtered dict containing only the fields
        listed in the spec
    """

    filtered = {}
    for name, value_type, default_value in spec:
        filtered[name] = get_checked_field(document, name,
                                           value_type, default_value)

    return filtered


def get_checked_field(document, name, value_type, default_value):
    """Validates and retrieves a typed field from a document.

    This function attempts to look up doc[name], and raises
    appropriate errors if the field is missing or not an
    instance of the given type.

    :param document: dict-like object
    :param name: field name
    :param value_type: expected value type, or '*' to accept any type
    :param default_value: Default value to use if the value is missing,
        or None to make the value required.
    :raises BadRequest: if the field is missing or not an
        instance of value_type
    :returns: value obtained from doc[name]
    """

    try:
        value = document[name]
    except KeyError:
        if default_value is not None:
            value = default_value
        else:
            description = _(u'Missing "{name}" field.').format(name=name)
            raise api_errors.BadRequest(description)

    # PERF(kgriffs): We do our own little spec thing because it is way
    # faster than jsonschema.
    if value_type == '*' or isinstance(value, value_type):
        return value

    description = _(u'The value of the "{name}" field must be a {vtype}.')
    description = description.format(name=name, vtype=value_type.__name__)
    raise api_errors.BadRequest(description)


def get_client_uuid(req):
    """Read a required Client-ID from a request.

    :param req: Request object
    :raises BadRequest: if the Client-ID header is missing or
        does not represent a valid UUID
    :returns: A UUID object
    """

    try:
        return uuid.UUID(req._headers.get('Client-ID'))
    except ValueError:
        description = _(u'Malformed hexadecimal UUID.')
        raise api_errors.BadRequest(description)


def get_headers(req):
    kwargs = {}

    # TODO(vkmc) We should add a control here to make sure
    # that the headers/request combination is possible
    # e.g. we cannot have messages_post with grace

    if req._body.get('marker') is not None:
        kwargs['marker'] = req._body.get('marker')

    if req._body.get('limit') is not None:
        kwargs['limit'] = int(req._body.get('limit'))

    if req._body.get('detailed') is not None:
        kwargs['detailed'] = strutils.bool_from_string(
            req._body.get('detailed'))

    if req._body.get('echo') is not None:
        kwargs['echo'] = strutils.bool_from_string(req._body.get('echo'))

    if req._body.get('include_claimed') is not None:
        kwargs['include_claimed'] = strutils.bool_from_string(
            req._body.get('include_claimed'))

    if req._body.get('ttl') is not None:
        kwargs['ttl'] = int(req._body.get('ttl'))

    if req._body.get('grace') is not None:
        kwargs['grace'] = int(req._body.get('grace'))

    return kwargs


def on_exception_sends_500(func):
    """Handles generic Exceptions in API endpoints

    This decorator catches generic Exceptions and returns a generic
    Response.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            LOG.exception(ex)
            error = _("Unexpected error.")
            headers = {'status': 500}
            # args[0] - Endpoints object, args[1] - Request object.
            req = args[1]
            return error_response(req, ex, headers, error)

    return wrapper


def error_response(req, exception, headers=None, error=None):
    body = {'exception': str(exception), 'error': error}
    resp = response.Response(req, body, headers)
    return resp


def format_message(message, claim_id=None):
    return {
        'id': message['id'],
        'claim_id': claim_id,
        'ttl': message['ttl'],
        'age': message['age'],
        'body': message['body'],
    }

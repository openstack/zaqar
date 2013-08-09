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
#
# See the License for the specific language governing permissions and
# limitations under the License.

import marconi.openstack.common.log as logging

from marconi.transport import utils
from marconi.transport.wsgi import exceptions


JSONObject = dict
"""Represents a JSON object in Python."""

JSONArray = list
"""Represents a JSON array in Python."""

LOG = logging.getLogger(__name__)


# TODO(kgriffs): Consider moving this to Falcon and/or Oslo
def filter_stream(stream, len, spec, doctype=JSONObject):
    """Reads, deserializes, and validates a document from a stream.

    :param stream: file-like object from which to read an object or
        array of objects.
    :param len: number of bytes to read from stream
    :param spec: iterable describing expected fields, yielding
        tuples with the form of: (field_name, value_type). Note that
        value_type may either be a Python type, or the special
        string '*' to accept any type.
    :param doctype: type of document to expect; must be either
        JSONObject or JSONArray.
    :raises: HTTPBadRequest, HTTPServiceUnavailable
    :returns: A sanitized, filtered version of the document read
        from the stream. If the document contains a list of objects,
        each object will be filtered and yielded in turn. If, on
        the other hand, the document is expected to contain a
        single object, that object will be filtered and returned as
        a single-element iterable.
    """

    try:
        # TODO(kgriffs): read_json should stream the resulting list
        # of messages, returning a generator rather than buffering
        # everything in memory (bp/streaming-serialization).
        document = utils.read_json(stream, len)

    except utils.MalformedJSON as ex:
        LOG.exception(ex)
        description = _('Body could not be parsed.')
        raise exceptions.HTTPBadRequestBody(description)

    except utils.OverflowedJSONInteger as ex:
        LOG.exception(ex)
        description = _('JSON contains integer that is too large.')
        raise exceptions.HTTPBadRequestBody(description)

    except Exception as ex:
        # Error while reading from the network/server
        LOG.exception(ex)
        description = _('Request body could not be read.')
        raise exceptions.HTTPServiceUnavailable(description)

    if doctype is JSONObject:
        if not isinstance(document, JSONObject):
            raise exceptions.HTTPDocumentTypeNotSupported()

        return (filter(document, spec),)

    if doctype is JSONArray:
        if not isinstance(document, JSONArray):
            raise exceptions.HTTPDocumentTypeNotSupported()

        # Return as a generator since we plan on doing a
        # streaming JSON deserializer (see above.git )
        return (filter(obj, spec) for obj in document)

    raise ValueError('doctype not in (JSONObject, JSONArray)')


# TODO(kgriffs): Consider moving this to Falcon and/or Oslo
def filter(document, spec):
    """Validates and retrieves typed fields from a single document.

    Sanitizes a dict-like document by checking it against a
    list of field spec, and returning only those fields
    specified.

    :param document: dict-like object
    :param spec: iterable describing expected fields, yielding
        tuples with the form of: (field_name, value_type). Note that
        value_type may either be a Python type, or the special
        string '*' to accept any type.
    :raises: HTTPBadRequest if any field is missing or not an
        instance of the specified type
    :returns: A filtered dict containing only the fields
        listed in the spec
    """

    filtered = {}
    for name, value_type in spec:
        filtered[name] = get_checked_field(document, name, value_type)

    return filtered


# TODO(kgriffs): Consider moving this to Falcon and/or Oslo
def get_checked_field(document, name, value_type):
    """Validates and retrieves a typed field from a document.

    This function attempts to look up doc[name], and raises
    appropriate HTTP errors if the field is missing or not an
    instance of the given type.

    :param document: dict-like object
    :param name: field name
    :param value_type: expected value type, or '*' to accept any type
    :raises: HTTPBadRequest if the field is missing or not an
        instance of value_type
    :returns: value obtained from doc[name]
    """

    try:
        value = document[name]
    except KeyError:
        description = _('Missing "{name}" field.').format(name=name)
        raise exceptions.HTTPBadRequestBody(description)

    if value_type == '*' or isinstance(value, value_type):
        return value

    description = _('The value of the "{name}" field must be a {vtype}.')
    description = description.format(name=name, vtype=value_type.__name__)
    raise exceptions.HTTPBadRequestBody(description)

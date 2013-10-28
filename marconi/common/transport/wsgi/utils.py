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

"""utils: a set of utilities to help with transport handling details."""

import jsonschema

from marconi.openstack.common import log
from marconi.queues.transport import utils as json_utils
from marconi.queues.transport.wsgi import errors as wsgi_errors

LOG = log.getLogger(__name__)


def load(req):
    """Reads request body, raising an exception if it is not JSON.

    :param req: The request object to read from
    :type req: falcon.Request
    :return: a dictionary decoded from the JSON stream
    :rtype: dict
    :raises: wsgi_errors.HTTPBadRequestBody
    """
    try:
        return json_utils.read_json(req.stream, req.content_length)
    except (json_utils.MalformedJSON, json_utils.OverflowedJSONInteger) as ex:
        LOG.exception(ex)
        raise wsgi_errors.HTTPBadRequestBody(
            'JSON could not be parsed.'
        )


# TODO(cpp-cabrera): generalize this
def validate(validator, document):
    """Verifies a document against a schema.

    :param validator: a validator to use to check validity
    :type validator: jsonschema.Draft4Validator
    :param document: document to check
    :type document: dict
    :raises: wsgi_errors.HTTPBadRequestBody
    """
    try:
        validator.validate(document)
    except jsonschema.ValidationError as ex:
        raise wsgi_errors.HTTPBadRequestBody(
            '{0}: {1}'.format(ex.args, ex.message)
        )

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

"""utils: utilities for transport handling."""

import jsonschema

from marconi.queues.transport.wsgi import exceptions as wsgi_errors


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

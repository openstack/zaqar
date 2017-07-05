# Copyright (c) 2013 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import jsonschema
from jsonschema import validators
from oslo_log import log

from zaqar.common import errors
from zaqar.i18n import _

LOG = log.getLogger(__name__)


class Api(object):

    schema = {}
    validators = {}

    def get_schema(self, action):
        """Returns the schema for an action

        :param action: Action for which params need
            to be validated.
        :type action: `six.text_type`

        :returns: Action's schema
        :rtype: dict

        :raises InvalidAction: if the action does not exist
        """

        try:
            return self.schema[action]
        except KeyError:
            msg = _('{0} is not a valid action').format(action)
            raise errors.InvalidAction(msg)

    def validate(self, action, body):
        """Validates the request data

        This method relies on jsonschema and exists
        just as a way for third-party transport to validate
        the request. It's not recommended to validate every
        request since they are already validated server side.

        :param action: Action's for which body need
            to be validated.
        :type action: `six.text_type`
        :param body: Params to validate
        :type body: dict

        :returns: True if the schema is valid, False otherwise
        :raises InvalidAction: if the action does not exist
        """

        if action not in self.validators:
            schema = self.get_schema(action)
            self.validators[action] = validators.Draft4Validator(schema)

        try:
            self.validators[action].validate(body)
        except jsonschema.ValidationError as ex:
            LOG.debug('Schema validation failed. %s.', str(ex))
            return False

        return True

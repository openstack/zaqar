# Copyright (c) 2014 Red Hat, Inc.
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
import jsonschema

from zaqar.common.schemas import flavors as schema
from zaqar.common import utils as common_utils
from zaqar.i18n import _
from zaqar.openstack.common import log
from zaqar.queues.storage import errors
from zaqar.queues.transport import utils as transport_utils
from zaqar.queues.transport.wsgi import errors as wsgi_errors
from zaqar.queues.transport.wsgi import utils as wsgi_utils

LOG = log.getLogger(__name__)


class Listing(object):
    """A resource to list registered flavors

    :param flavors_controller: means to interact with storage
    """

    def __init__(self, flavors_controller):
        self._ctrl = flavors_controller

    def on_get(self, request, response, project_id):
        """Returns a flavor listing as objects embedded in an array:

        ::

            [
                {"href": "", "capabilities": {}, "pool": ""},
                ...
            ]

        :returns: HTTP | [200, 204]
        """

        LOG.debug(u'LIST flavors for project_id %s' % project_id)

        store = {}
        request.get_param('marker', store=store)
        request.get_param_as_int('limit', store=store)
        request.get_param_as_bool('detailed', store=store)

        results = {}
        results['flavors'] = list(self._ctrl.list(project=project_id, **store))
        for entry in results['flavors']:
            entry['href'] = request.path + '/' + entry.pop('name')

        if not results['flavors']:
            response.status = falcon.HTTP_204
            return

        response.body = transport_utils.to_json(results)
        response.status = falcon.HTTP_200


class Resource(object):
    """A handler for individual flavor.

    :param flavors_controller: means to interact with storage
    """

    def __init__(self, flavors_controller):
        self._ctrl = flavors_controller
        validator_type = jsonschema.Draft4Validator
        self._validators = {
            'create': validator_type(schema.create),
            'pool': validator_type(schema.patch_pool),
            'capabilities': validator_type(schema.patch_capabilities),
        }

    def on_get(self, request, response, project_id, flavor):
        """Returns a JSON object for a single flavor entry:

        ::

            {"pool": "", capabilities: {...}}

        :returns: HTTP | [200, 404]
        """

        LOG.debug(u'GET flavor - name: %s', flavor)
        data = None
        detailed = request.get_param_as_bool('detailed') or False

        try:
            data = self._ctrl.get(flavor,
                                  project=project_id,
                                  detailed=detailed)

        except errors.FlavorDoesNotExist as ex:
            LOG.debug(ex)
            raise falcon.HTTPNotFound()

        data['href'] = request.path

        # remove the name entry - it isn't needed on GET
        del data['name']
        response.body = transport_utils.to_json(data)

    def on_put(self, request, response, project_id, flavor):
        """Registers a new flavor. Expects the following input:

        ::

            {"pool": "my-pool", "capabilities": {}}

        A capabilities object may also be provided.

        :returns: HTTP | [201, 400]
        """

        LOG.debug(u'PUT flavor - name: %s', flavor)

        data = wsgi_utils.load(request)
        wsgi_utils.validate(self._validators['create'], data)

        try:
            self._ctrl.create(flavor,
                              pool=data['pool'],
                              project=project_id,
                              capabilities=data['capabilities'])
            response.status = falcon.HTTP_201
            response.location = request.path
        except errors.PoolDoesNotExist as ex:
            LOG.exception(ex)
            description = (_(u'Flavor {flavor} could not be created. '
                             u'Pool {pool} does not exist') %
                           dict(flavor=flavor, pool=data['pool']))
            raise falcon.HTTPBadRequest(_('Unable to create'), description)

    def on_delete(self, request, response, project_id, flavor):
        """Deregisters a flavor.

        :returns: HTTP | [204]
        """

        LOG.debug(u'DELETE flavor - name: %s', flavor)
        self._ctrl.delete(flavor, project=project_id)
        response.status = falcon.HTTP_204

    def on_patch(self, request, response, project_id, flavor):
        """Allows one to update a flavors's pool and/or capabilities.

        This method expects the user to submit a JSON object
        containing at least one of: 'pool', 'capabilities'. If
        none are found, the request is flagged as bad. There is also
        strict format checking through the use of
        jsonschema. Appropriate errors are returned in each case for
        badly formatted input.

        :returns: HTTP | [200, 400]
        """

        LOG.debug(u'PATCH flavor - name: %s', flavor)
        data = wsgi_utils.load(request)

        EXPECT = ('pool', 'capabilities')
        if not any([(field in data) for field in EXPECT]):
            LOG.debug(u'PATCH flavor, bad params')
            raise wsgi_errors.HTTPBadRequestBody(
                'One of `pool` or `capabilities` needs '
                'to be specified'
            )

        for field in EXPECT:
            wsgi_utils.validate(self._validators[field], data)

        fields = common_utils.fields(data, EXPECT,
                                     pred=lambda v: v is not None)

        try:
            self._ctrl.update(flavor, project=project_id, **fields)
        except errors.FlavorDoesNotExist as ex:
            LOG.exception(ex)
            raise falcon.HTTPNotFound()

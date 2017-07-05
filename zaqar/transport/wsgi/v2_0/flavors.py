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
from oslo_log import log
import six

from zaqar.common.api.schemas import flavors as schema
from zaqar.common import decorators
from zaqar.common import utils as common_utils
from zaqar.i18n import _
from zaqar.storage import errors
from zaqar.transport import acl
from zaqar.transport import utils as transport_utils
from zaqar.transport import validation
from zaqar.transport.wsgi import errors as wsgi_errors
from zaqar.transport.wsgi import utils as wsgi_utils

LOG = log.getLogger(__name__)


class Listing(object):
    """A resource to list registered flavors

    :param flavors_controller: means to interact with storage
    """

    def __init__(self, flavors_controller, pools_controller, validate):
        self._ctrl = flavors_controller
        self._pools_ctrl = pools_controller
        self._validate = validate

    @decorators.TransportLog("Flavors collection")
    @acl.enforce("flavors:get_all")
    def on_get(self, request, response, project_id):
        """Returns a flavor listing as objects embedded in an object:

        ::

            {
                "flavors": [
                    {"href": "", "capabilities": {}, "pool_group": ""},
                    ...
                ],
                "links": [
                    {"rel": "next", "href": ""},
                    ...
                ]
            }

        :returns: HTTP | 200
        """

        LOG.debug(u'LIST flavors for project_id %s', project_id)

        store = {}
        request.get_param('marker', store=store)
        request.get_param_as_int('limit', store=store)
        detailed = request.get_param_as_bool('detailed')

        try:
            self._validate.flavor_listing(**store)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        cursor = self._ctrl.list(project=project_id, **store)
        flavors = list(next(cursor))

        results = {'links': []}

        if flavors:
            store['marker'] = next(cursor)

            for entry in flavors:
                entry['href'] = request.path + '/' + entry['name']
                pool_group = entry['pool_group']
                # NOTE(wanghao): remove this in Newton.
                entry['pool'] = entry['pool_group']
                if detailed:
                    caps = self._pools_ctrl.capabilities(group=pool_group)
                    entry['capabilities'] = [str(cap).split('.')[-1]
                                             for cap in caps]

        if detailed is not None:
            store['detailed'] = detailed

        if flavors:
            results['links'] = [
                {
                    'rel': 'next',
                    'href': request.path + falcon.to_query_str(store)
                }
            ]

        results['flavors'] = flavors

        response.body = transport_utils.to_json(results)
        response.status = falcon.HTTP_200


class Resource(object):
    """A handler for individual flavor.

    :param flavors_controller: means to interact with storage
    """

    def __init__(self, flavors_controller, pools_controller):
        self._ctrl = flavors_controller
        self._pools_ctrl = pools_controller

        validator_type = jsonschema.Draft4Validator
        self._validators = {
            'create': validator_type(schema.create),
            'pool_group': validator_type(schema.patch_pool_group),
            # NOTE(wanghao): Remove this in Newton.
            'pool': validator_type(schema.patch_pool),
            'capabilities': validator_type(schema.patch_capabilities),
        }

    @decorators.TransportLog("Flavors item")
    @acl.enforce("flavors:get")
    def on_get(self, request, response, project_id, flavor):
        """Returns a JSON object for a single flavor entry:

        ::

            {"pool": "", capabilities: {...}}

        :returns: HTTP | [200, 404]
        """

        LOG.debug(u'GET flavor - name: %s', flavor)
        data = None

        try:
            data = self._ctrl.get(flavor, project=project_id)
            pool_group = data['pool_group']
            # NOTE(wanghao): remove this in Newton.
            data['pool'] = data['pool_group']
            capabilities = self._pools_ctrl.capabilities(group=pool_group)
            data['capabilities'] = [str(cap).split('.')[-1]
                                    for cap in capabilities]

        except errors.FlavorDoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))

        data['href'] = request.path

        response.body = transport_utils.to_json(data)

    @decorators.TransportLog("Flavors item")
    @acl.enforce("flavors:create")
    def on_put(self, request, response, project_id, flavor):
        """Registers a new flavor. Expects the following input:

        ::

            {"pool_group": "my-pool-group", "capabilities": {}}

        A capabilities object may also be provided.

        :returns: HTTP | [201, 400]
        """

        LOG.debug(u'PUT flavor - name: %s', flavor)

        data = wsgi_utils.load(request)
        wsgi_utils.validate(self._validators['create'], data)
        pool_group = data.get('pool_group') or data.get('pool')
        capabilities = self._pools_ctrl.capabilities(pool_group)
        try:
            self._ctrl.create(flavor,
                              pool_group=pool_group,
                              project=project_id,
                              capabilities=capabilities)
            response.status = falcon.HTTP_201
            response.location = request.path
        except errors.PoolGroupDoesNotExist as ex:
            LOG.exception(ex)
            description = (_(u'Flavor %(flavor)s could not be created. '
                             u'Pool group %(pool_group)s does not exist') %
                           dict(flavor=flavor, pool_group=pool_group))
            raise falcon.HTTPBadRequest(_('Unable to create'), description)

    @decorators.TransportLog("Flavors item")
    @acl.enforce("flavors:delete")
    def on_delete(self, request, response, project_id, flavor):
        """Deregisters a flavor.

        :returns: HTTP | [204]
        """

        LOG.debug(u'DELETE flavor - name: %s', flavor)
        self._ctrl.delete(flavor, project=project_id)
        response.status = falcon.HTTP_204

    @decorators.TransportLog("Flavors item")
    @acl.enforce("flavors:update")
    def on_patch(self, request, response, project_id, flavor):
        """Allows one to update a flavors's pool_group.

        This method expects the user to submit a JSON object
        containing 'pool_group'. If none is found, the request is flagged
        as bad. There is also strict format checking through the use of
        jsonschema. Appropriate errors are returned in each case for
        badly formatted input.

        :returns: HTTP | [200, 400]
        """

        LOG.debug(u'PATCH flavor - name: %s', flavor)
        data = wsgi_utils.load(request)

        EXPECT = ('pool_group', 'pool')
        if not any([(field in data) for field in EXPECT]):
            LOG.debug(u'PATCH flavor, bad params')
            raise wsgi_errors.HTTPBadRequestBody(
                '`pool_group` or `pool` needs to be specified'
            )

        for field in EXPECT:
            wsgi_utils.validate(self._validators[field], data)

        fields = common_utils.fields(data, EXPECT,
                                     pred=lambda v: v is not None)
        # NOTE(wanghao): remove this in Newton.
        if fields.get('pool') and fields.get('pool_group') is None:
            fields['pool_group'] = fields.get('pool')
            fields.pop('pool')

        resp_data = None
        try:
            self._ctrl.update(flavor, project=project_id, **fields)
            resp_data = self._ctrl.get(flavor, project=project_id)
            capabilities = self._pools_ctrl.capabilities(
                group=resp_data['pool_group'])
            resp_data['capabilities'] = [str(cap).split('.')[-1]
                                         for cap in capabilities]
        except errors.FlavorDoesNotExist as ex:
            LOG.exception(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))
        resp_data['href'] = request.path
        response.body = transport_utils.to_json(resp_data)

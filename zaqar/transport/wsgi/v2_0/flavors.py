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

from zaqar.common.api.schemas import flavors as schema
from zaqar.common import decorators
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
                    {"href": "", "capabilities": {},
                     "pool_list": ""},
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
            raise wsgi_errors.HTTPBadRequestAPI(str(ex))

        cursor = self._ctrl.list(project=project_id, **store)
        flavors = list(next(cursor))

        results = {'links': []}

        if flavors:
            store['marker'] = next(cursor)

            for entry in flavors:
                entry['href'] = request.path + '/' + entry['name']
                data = {}
                data['name'] = entry['name']
                pool_list = \
                    list(self._pools_ctrl.get_pools_by_flavor(flavor=data))
                pool_name_list = []
                if len(pool_list) > 0:
                    pool_name_list = [x['name'] for x in pool_list]
                    entry['pool_list'] = pool_name_list
                if detailed:
                    caps = self._pools_ctrl.capabilities(flavor=entry)
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
            'pool_list': validator_type(schema.patch_pool_list),
            'capabilities': validator_type(schema.patch_capabilities),
        }

    @decorators.TransportLog("Flavors item")
    @acl.enforce("flavors:get")
    def on_get(self, request, response, project_id, flavor):
        """Returns a JSON object for a single flavor entry:

        ::

            {"pool": "", "pool_list": [], capabilities: {...}}

        :returns: HTTP | [200, 404]
        """

        LOG.debug(u'GET flavor - name: %s', flavor)
        data = None

        try:
            data = self._ctrl.get(flavor, project=project_id)
            capabilities = self._pools_ctrl.capabilities(flavor=data)
            data['capabilities'] = [str(cap).split('.')[-1]
                                    for cap in capabilities]
            pool_list =\
                list(self._pools_ctrl.get_pools_by_flavor(flavor=data))
            pool_name_list = []
            if len(pool_list) > 0:
                pool_name_list = [x['name'] for x in pool_list]
            data['pool_list'] = pool_name_list

        except errors.FlavorDoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(str(ex))

        data['href'] = request.path

        response.body = transport_utils.to_json(data)

    def _check_pools_exists(self, pool_list):
        if pool_list is not None:
            for pool in pool_list:
                if not self._pools_ctrl.exists(pool):
                    raise errors.PoolDoesNotExist(pool)

    def _update_pools_by_flavor(self, flavor, pool_list):
        if pool_list is not None:
            for pool in pool_list:
                self._pools_ctrl.update(pool, flavor=flavor)

    def _clean_pools_by_flavor(self, flavor, pool_list=None):
        if pool_list is None:
            flavor_obj = {}
            flavor_obj['name'] = flavor
            pllt = list(self._pools_ctrl.get_pools_by_flavor(
                flavor=flavor_obj))
            pool_list = [x['name'] for x in pllt]
        if pool_list is not None:
            for pool in pool_list:
                self._pools_ctrl.update(pool, flavor="")

    def _on_put_by_pool_list(self, request, response, project_id,
                             flavor, pool_list):
        LOG.debug(u'PUT flavor - name by flavor: %s', flavor)
        # NOTE(gengchc2): If configuration flavor is used by the new schema,
        # a list of pools is required.
        if len(pool_list) == 0:
            response.status = falcon.HTTP_400
            response.location = request.path
            raise falcon.HTTPBadRequest(_('Unable to create'), 'Bad Request')
        # NOTE(gengchc2): Check if pools in the pool_list exist.
        try:
            self._check_pools_exists(pool_list)
        except errors.PoolDoesNotExist as ex:
            description = (_(u'Flavor %(flavor)s could not be created, '
                             'error:%(msg)s') %
                           dict(flavor=flavor, msg=str(ex)))
            LOG.exception(description)
            raise falcon.HTTPBadRequest(_('Unable to create'), description)
        capabilities = self._pools_ctrl.capabilities(name=pool_list[0])
        try:
            self._ctrl.create(flavor,
                              project=project_id,
                              capabilities=capabilities)
            response.status = falcon.HTTP_201
            response.location = request.path
        except errors.ConnectionError as ex:
            description = (_(u'Flavor %(flavor)s could not be created, '
                             'error:%(msg)s') %
                           dict(flavor=flavor, msg=str(ex)))
            LOG.exception(description)
            raise falcon.HTTPBadRequest(_('Unable to create'), description)
        # NOTE(gengchc2): Update the 'flavor' field in pools tables.
        try:
            self._update_pools_by_flavor(flavor, pool_list)
        except errors.ConnectionError as ex:
            description = (_(u'Flavor %(flavor)s could not be created, '
                             'error:%(msg)s') %
                           dict(flavor=flavor, msg=str(ex)))
            LOG.exception(description)
            raise falcon.HTTPBadRequest(_('Unable to create'), description)

    @decorators.TransportLog("Flavors item")
    @acl.enforce("flavors:create")
    def on_put(self, request, response, project_id, flavor):
        """Registers a new flavor. Expects the following input:

        ::

            {"pool_list": [], "capabilities": {}}

        A capabilities object may also be provided.

        :returns: HTTP | [201, 400]
        """

        LOG.debug(u'PUT flavor - name: %s', flavor)

        data = wsgi_utils.load(request)
        wsgi_utils.validate(self._validators['create'], data)
        pool_list = data.get('pool_list')
        if pool_list is not None:
            self._on_put_by_pool_list(request, response, project_id,
                                      flavor, pool_list)

    @decorators.TransportLog("Flavors item")
    @acl.enforce("flavors:delete")
    def on_delete(self, request, response, project_id, flavor):
        """Deregisters a flavor.

        :returns: HTTP | [204]
        """

        LOG.debug(u'DELETE flavor - name: %s', flavor)
        # NOTE(gengchc2): If configuration flavor is
        # used by the new schema, the flavor field in pools
        # need to be cleaned.
        try:
            self._clean_pools_by_flavor(flavor)
        except errors.ConnectionError:
            description = (_(u'Flavor %(flavor)s could not be deleted.') %
                           dict(flavor=flavor))
            LOG.exception(description)
            raise falcon.HTTPBadRequest(_('Unable to create'), description)
        self._ctrl.delete(flavor, project=project_id)
        response.status = falcon.HTTP_204

    def _on_patch_by_pool_list(self, request, response, project_id,
                               flavor, pool_list):

        if len(pool_list) == 0:
            response.status = falcon.HTTP_400
            response.location = request.path
            raise falcon.HTTPBadRequest(_('Unable to create'), 'Bad Request')
        # NOTE(gengchc2): If the flavor does not exist, return
        try:
            self._ctrl.get(flavor, project=project_id)
        except errors.FlavorDoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(str(ex))

        flavor_obj = {}
        flavor_obj['name'] = flavor
        # NOTE(gengchc2): Get the pools list with flavor.
        pool_list_old = list(self._pools_ctrl.get_pools_by_flavor(
            flavor=flavor_obj))
        # NOTE(gengchc2): Check if the new pool in the pool_list exist.
        try:
            self._check_pools_exists(pool_list)
        except errors.PoolDoesNotExist as ex:
            description = (_(u'Flavor %(flavor)s cant be updated, '
                             'error:%(msg)s') %
                           dict(flavor=flavor, msg=str(ex)))
            LOG.exception(description)
            raise falcon.HTTPBadRequest(_('updatefail'), description)
        capabilities = self._pools_ctrl.capabilities(name=pool_list[0])
        try:
            self._ctrl.update(flavor, project=project_id,
                              capabilities=capabilities)
            resp_data = self._ctrl.get(flavor, project=project_id)
            resp_data['capabilities'] = [str(cap).split('.')[-1]
                                         for cap in capabilities]
        except errors.FlavorDoesNotExist as ex:
            LOG.exception('Flavor "%s" does not exist', flavor)
            raise wsgi_errors.HTTPNotFound(str(ex))

        # (gengchc) Update flavor field in new pool list.
        try:
            self._update_pools_by_flavor(flavor, pool_list)
        except errors.ConnectionError as ex:
            description = (_(u'Flavor %(flavor)s could not be updated, '
                             'error:%(msg)s') %
                           dict(flavor=flavor, msg=str(ex)))
            LOG.exception(description)
            raise falcon.HTTPBadRequest(_('Unable to create'), description)
        # (gengchc) Remove flavor from old pool list.
        try:
            pool_list_removed = []
            for pool_old in pool_list_old:
                if pool_old['name'] not in pool_list:
                    pool_list_removed.append(pool_old['name'])
            self._clean_pools_by_flavor(flavor, pool_list_removed)
        except errors.ConnectionError as ex:
            description = (_(u'Flavor %(flavor)s could not be updated, '
                             'error:%(msg)s') %
                           dict(flavor=flavor, msg=str(ex)))
            LOG.exception(description)
            raise falcon.HTTPBadRequest(_('Unable to create'), description)
        resp_data['pool_list'] = pool_list
        resp_data['href'] = request.path
        response.body = transport_utils.to_json(resp_data)

    @decorators.TransportLog("Flavors item")
    @acl.enforce("flavors:update")
    def on_patch(self, request, response, project_id, flavor):
        """Allows one to update a flavors'pool list.

        This method expects the user to submit a JSON object
        containing 'pool list'. If none is found,
        the request is flagged as bad. There is also strict format
        checking through the use of jsonschema. Appropriate errors
        are returned in each case for badly formatted input.

        :returns: HTTP | [200, 400]
        """
        LOG.debug(u'PATCH flavor - name: %s', flavor)
        data = wsgi_utils.load(request)
        field = 'pool_list'
        if field not in data:
            LOG.debug(u'PATCH flavor, bad params')
            raise wsgi_errors.HTTPBadRequestBody(
                '`pool_list` needs to be specified'
            )

        wsgi_utils.validate(self._validators[field], data)
        pool_list = data.get('pool_list')
        # NOTE(gengchc2): If pool_list is not None, configuration flavor is
        # used by the new schema.
        # a list of pools is required.
        if pool_list is not None:
            self._on_patch_by_pool_list(request, response, project_id,
                                        flavor, pool_list)

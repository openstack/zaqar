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

"""pools: a resource to handle storage pool management

A pool is added by an operator by interacting with the
pooling-related endpoints. When specifying a pool, the
following fields are required:

::

    {
        "name": string,
        "weight": integer,
        "uri": string::uri
    }

Furthermore, depending on the underlying storage type of pool being
registered, there is an optional field:
::

    {
        "options": {...}
    }
"""

import falcon
import jsonschema
from oslo_log import log
import six

from zaqar.common.api.schemas import pools as schema
from zaqar.common import decorators
from zaqar.common import utils as common_utils
from zaqar.i18n import _
from zaqar.storage import errors
from zaqar.storage import utils as storage_utils
from zaqar.transport import acl
from zaqar.transport import utils as transport_utils
from zaqar.transport import validation
from zaqar.transport.wsgi import errors as wsgi_errors
from zaqar.transport.wsgi import utils as wsgi_utils

LOG = log.getLogger(__name__)


class Listing(object):
    """A resource to list registered pools

    :param pools_controller: means to interact with storage
    """

    def __init__(self, pools_controller, validate):
        self._ctrl = pools_controller
        self._validate = validate

    @decorators.TransportLog("Pools collection")
    @acl.enforce("pools:get_all")
    def on_get(self, request, response, project_id):
        """Returns a pool listing as objects embedded in an object:

        ::

            {
                "pools": [
                    {"href": "", "weight": 100, "uri": ""},
                    ...
                ],
                "links": [
                    {"href": "", "rel": "next"}
                ]
            }

        :returns: HTTP | 200
        """

        LOG.debug(u'LIST pools')

        store = {}
        request.get_param('marker', store=store)
        request.get_param_as_int('limit', store=store)
        request.get_param_as_bool('detailed', store=store)

        try:
            self._validate.pool_listing(**store)
        except validation.ValidationFailed as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPBadRequestAPI(six.text_type(ex))

        cursor = self._ctrl.list(**store)
        pools = list(next(cursor))

        results = {'links': []}

        if pools:
            store['marker'] = next(cursor)

            for entry in pools:
                entry['href'] = request.path + '/' + entry['name']

            results['links'] = [
                {
                    'rel': 'next',
                    'href': request.path + falcon.to_query_str(store)
                }
            ]

        results['pools'] = pools

        response.content_location = request.relative_uri
        response.body = transport_utils.to_json(results)
        response.status = falcon.HTTP_200


class Resource(object):
    """A handler for individual pool.

    :param pools_controller: means to interact with storage
    """

    def __init__(self, pools_controller):
        self._ctrl = pools_controller
        validator_type = jsonschema.Draft4Validator
        self._validators = {
            'weight': validator_type(schema.patch_weight),
            'uri': validator_type(schema.patch_uri),
            'group': validator_type(schema.patch_uri),
            'options': validator_type(schema.patch_options),
            'create': validator_type(schema.create)
        }

    @decorators.TransportLog("Pools item")
    @acl.enforce("pools:get")
    def on_get(self, request, response, project_id, pool):
        """Returns a JSON object for a single pool entry:

        ::

            {"weight": 100, "uri": "", options: {...}}

        :returns: HTTP | [200, 404]
        """

        LOG.debug(u'GET pool - name: %s', pool)
        data = None
        detailed = request.get_param_as_bool('detailed') or False

        try:
            data = self._ctrl.get(pool, detailed)

        except errors.PoolDoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))

        data['href'] = request.path

        response.body = transport_utils.to_json(data)

    @decorators.TransportLog("Pools item")
    @acl.enforce("pools:create")
    def on_put(self, request, response, project_id, pool):
        """Registers a new pool. Expects the following input:

        ::

            {"weight": 100, "uri": ""}

        An options object may also be provided.

        :returns: HTTP | [201, 204]
        """

        LOG.debug(u'PUT pool - name: %s', pool)

        conf = self._ctrl.driver.conf
        data = wsgi_utils.load(request)
        wsgi_utils.validate(self._validators['create'], data)
        if not storage_utils.can_connect(data['uri'], conf=conf):
            raise wsgi_errors.HTTPBadRequestBody(
                'cannot connect to %s' % data['uri']
            )
        try:
            self._ctrl.create(pool, weight=data['weight'],
                              uri=data['uri'],
                              group=data.get('group'),
                              options=data.get('options', {}))
            response.status = falcon.HTTP_201
            response.location = request.path
        except errors.PoolCapabilitiesMismatch as e:
            LOG.exception(e)
            title = _(u'Unable to create pool')
            raise falcon.HTTPBadRequest(title, six.text_type(e))
        except errors.PoolAlreadyExists as e:
            LOG.exception(e)
            raise wsgi_errors.HTTPConflict(six.text_type(e))

    @decorators.TransportLog("Pools item")
    @acl.enforce("pools:delete")
    def on_delete(self, request, response, project_id, pool):
        """Deregisters a pool.

        :returns: HTTP | [204, 403]
        """

        LOG.debug(u'DELETE pool - name: %s', pool)

        try:
            self._ctrl.delete(pool)
        except errors.PoolInUseByFlavor as ex:
            LOG.exception(ex)
            title = _(u'Unable to delete')
            description = _(u'This pool is used by flavors {flavor}; '
                            u'It cannot be deleted.')
            description = description.format(flavor=ex.flavor)
            raise falcon.HTTPForbidden(title, description)

        response.status = falcon.HTTP_204

    @decorators.TransportLog("Pools item")
    @acl.enforce("pools:update")
    def on_patch(self, request, response, project_id, pool):
        """Allows one to update a pool's weight, uri, and/or options.

        This method expects the user to submit a JSON object
        containing at least one of: 'uri', 'weight', 'group', 'options'. If
        none are found, the request is flagged as bad. There is also
        strict format checking through the use of
        jsonschema. Appropriate errors are returned in each case for
        badly formatted input.

        :returns: HTTP | 200,400
        """

        LOG.debug(u'PATCH pool - name: %s', pool)
        data = wsgi_utils.load(request)

        EXPECT = ('weight', 'uri', 'group', 'options')
        if not any([(field in data) for field in EXPECT]):
            LOG.debug(u'PATCH pool, bad params')
            raise wsgi_errors.HTTPBadRequestBody(
                'One of `uri`, `weight`, `group`, or `options` needs '
                'to be specified'
            )

        for field in EXPECT:
            wsgi_utils.validate(self._validators[field], data)

        conf = self._ctrl.driver.conf
        if 'uri' in data and not storage_utils.can_connect(data['uri'],
                                                           conf=conf):
            raise wsgi_errors.HTTPBadRequestBody(
                'cannot connect to %s' % data['uri']
            )
        fields = common_utils.fields(data, EXPECT,
                                     pred=lambda v: v is not None)
        resp_data = None
        try:
            self._ctrl.update(pool, **fields)
            resp_data = self._ctrl.get(pool, False)
        except errors.PoolDoesNotExist as ex:
            LOG.exception(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))

        resp_data['href'] = request.path
        response.body = transport_utils.to_json(resp_data)

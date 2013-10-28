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

"""shards: a resource to handle storage shard management

A shard is added by an operator by interacting with the
sharding-related endpoints. When specifying a shard, the
following fields are required:

{
    "name": string,
    "weight": integer,
    "location": string::uri
}

Furthermore, depending on the underlying storage type of shard being
registered, there is an optional field:

{
    "options": {...}
}
"""

import falcon
import jsonschema

from marconi.common.schemas import shards as schema
from marconi.common.transport.wsgi import utils
from marconi.openstack.common import log
from marconi.proxy.storage import errors
from marconi.queues.transport import utils as transport_utils
from marconi.queues.transport.wsgi import errors as wsgi_errors

LOG = log.getLogger(__name__)


class Listing(object):
    """A resource to list registered partition

    :param partitions_controller: means to interact with storage
    """
    def __init__(self, partitions_controller):
        self._ctrl = partitions_controller

    def on_get(self, request, response):
        """Returns a partition listing as a JSON object:

        [
            {"name": "", "weight": 100, "location": ""},
            ...
        ]

        :returns: HTTP | [200, 204]
        """
        LOG.debug(u'LIST shards')
        resp = list(self._ctrl.list())

        if not resp:
            response.status = falcon.HTTP_204
            return

        response.body = transport_utils.to_json(resp)
        response.status = falcon.HTTP_200


class Resource(object):
    """A handler for individual partitions

    :param partitions_controller: means to interact with storage
    """
    def __init__(self, shards_controller):
        self._ctrl = shards_controller
        validator_type = jsonschema.Draft4Validator
        self._validators = {
            'weight': validator_type(schema.patch_weight),
            'location': validator_type(schema.patch_location),
            'options': validator_type(schema.patch_options),
            'create': validator_type(schema.create)
        }

    def on_get(self, request, response, shard):
        """Returns a JSON object for a single shard entry:

        {"weight": 100, "location": "", options: {...}}

        :returns: HTTP | [200, 404]
        """
        LOG.debug(u'GET shard - name: %s', shard)
        data = None
        try:
            data = self._ctrl.get(shard)
        except errors.ShardDoesNotExist as ex:
            LOG.exception(ex)
            raise falcon.HTTPNotFound()

        # remove the name entry - it isn't needed on GET
        del data['name']
        response.body = transport_utils.to_json(data)
        response.content_location = request.path

    def on_put(self, request, response, shard):
        """Registers a new shard. Expects the following input:

        {"weight": 100, "location": ""}

        An options object may also be provided.

        :returns: HTTP | [201, 204]
        """
        LOG.debug(u'PUT shard - name: %s', shard)
        if self._ctrl.exists(shard):
            LOG.debug(u'Shard %s already exists', shard)
            response.status = falcon.HTTP_204
            return

        data = utils.load(request)
        utils.validate(self._validators['create'], data)
        self._ctrl.create(shard, weight=data['weight'],
                          location=data['location'],
                          options=data.get('options', {}))
        response.status = falcon.HTTP_201
        response.location = request.path

    def on_delete(self, request, response, shard):
        """Deregisters a shard.

        :returns: HTTP | 204
        """
        LOG.debug(u'DELETE shard - name: %s', shard)
        self._ctrl.delete(shard)
        response.status = falcon.HTTP_204

    def on_patch(self, request, response, shard):
        """Allows one to update a shard's weight, location, and/or options.

        This method expects the user to submit a JSON object
        containing atleast one of: 'hosts', 'weight', 'options'. If
        none are found, the request is flagged as bad. There is also
        strict format checking through the use of
        jsonschema. Appropriate errors are returned in each case for
        badly formatted input.

        :returns: HTTP | 200,400
        """
        LOG.debug(u'PATCH shard - name: %s', shard)
        data = utils.load(request)

        EXPECT = ('weight', 'location', 'options')
        if not any([(field in data) for field in EXPECT]):
            LOG.debug(u'PATCH shard, bad params')
            raise wsgi_errors.HTTPBadRequestBody(
                'One of `location`, `weight`, or `options` needs '
                'to be specified'
            )

        for field in EXPECT:
            utils.validate(self._validators[field], data)

        try:
            fields = dict((k, v) for k, v in data.items()
                          if k in EXPECT and v is not None)

            self._ctrl.update(shard, **fields)
        except errors.ShardDoesNotExist as ex:
            LOG.exception(ex)
            raise falcon.HTTPNotFound()

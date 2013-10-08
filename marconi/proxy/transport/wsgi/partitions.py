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
"""partitions: a registry of all marconi partitions this proxy can route to

A partition is added by an operator by interacting with the
partition-related endpoints. When specifying a partition, the
following fields are required:

{
    "name": String,
    "weight": Integer,
    "hosts": [HTTP_EndPoints(:Port), ...]
}
"""
import json

import falcon
import jsonschema
import six

from marconi.openstack.common import log
from marconi.proxy.storage import exceptions
from marconi.proxy.transport import schema, utils
from marconi.proxy.utils import lookup
from marconi.queues.transport import utils as json_utils
from marconi.queues.transport.wsgi import exceptions as wsgi_errors

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


class Listing(object):
    """A resource to list registered partition

    :param partitions_controller: means to interact with storage
    """
    def __init__(self, partitions_controller):
        self._ctrl = partitions_controller

    def on_get(self, request, response):
        """Returns a partition listing as a JSON object:

        [
            {"name": "", "weight": 100, "hosts": [""]},
            ...
        ]

        :returns: HTTP | [200, 204]
        """
        LOG.debug('LIST partitions')
        resp = list(self._ctrl.list())

        if not resp:
            response.status = falcon.HTTP_204
            return

        response.body = json.dumps(resp, ensure_ascii=False)
        response.status = falcon.HTTP_200


class Resource(object):
    """A handler for individual partitions

    :param partitions_controller: means to interact with storage
    """
    def __init__(self, partitions_controller, cache_driver):
        self._ctrl = partitions_controller
        self._cache = cache_driver
        validator_type = jsonschema.Draft4Validator
        self._put_validator = validator_type(schema.partition_create)
        self._hosts_validator = validator_type(schema.partition_patch_hosts)
        self._weight_validator = validator_type(schema.partition_patch_weight)

    def on_get(self, request, response, partition):
        """Returns a JSON object for a single partition entry:

        {"weight": 100, "hosts": [""]}

        :returns: HTTP | [200, 404]
        """
        LOG.debug('GET partition - name: {0}'.format(partition))
        data = None
        try:
            data = self._ctrl.get(partition)
        except exceptions.PartitionNotFound as ex:
            LOG.exception(ex)
            raise falcon.HTTPNotFound()

        # getting a specific partition has no 'name' entry
        del data['name']
        response.body = json.dumps(data, ensure_ascii=False)

    def on_put(self, request, response, partition):
        """Creates a new partition. Expects the following input:

        {"weight": 100, "hosts": [""]}

        :returns: HTTP | [201, 204]
        """
        LOG.debug('PUT partition - name: {0}'.format(partition))
        if self._ctrl.exists(partition):
            LOG.debug('Partition {0} already exists'.format(partition))
            response.status = falcon.HTTP_204
            return

        data = load(request)
        utils.validate(self._put_validator, data)
        self._ctrl.create(partition,
                          weight=data['weight'],
                          hosts=data['hosts'])
        response.status = falcon.HTTP_201

    def on_delete(self, request, response, partition):
        """Removes an existing partition.

        :returns: HTTP | 204
        """
        LOG.debug('DELETE partition - name: {0}'.format(partition))
        lookup.invalidate_partition(partition, self._cache)
        self._ctrl.delete(partition)
        response.status = falcon.HTTP_204

    def on_patch(self, request, response, partition):
        """Allows one to update a partition's weight and/or hosts.

        This method expects the user to submit a JSON object
        containing both or either of 'hosts' and 'weight'. If neither
        is found, the request is flagged as bad. There is also strict
        format checking through the use of jsonschema. Appropriate
        errors are returned in each case for badly formatted input.

        :returns: HTTP | 200,400

        """
        LOG.debug('PATCH partition - name: {0}'.format(partition))
        data = load(request)

        if 'weight' not in data and 'hosts' not in data:
            LOG.debug('PATCH partition, bad params')
            raise wsgi_errors.HTTPBadRequestBody(
                'One of `hosts` or `weight` needs to be specified'
            )

        utils.validate(self._weight_validator, data)
        utils.validate(self._hosts_validator, data)
        try:
            fields = dict((k, v) for k, v in six.iteritems(data)
                          if k in ('hosts', 'weight')
                          and v is not None)

            self._ctrl.update(partition, **fields)
        except exceptions.PartitionNotFound as ex:
            LOG.exception(ex)
            raise falcon.HTTPNotFound()

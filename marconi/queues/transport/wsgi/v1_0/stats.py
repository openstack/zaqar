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
# See the License for the specific language governing permissions and
# limitations under the License.

import falcon

from marconi.openstack.common.gettextutils import _
import marconi.openstack.common.log as logging
from marconi.queues.storage import errors as storage_errors
from marconi.queues.transport import utils
from marconi.queues.transport.wsgi import errors as wsgi_errors


LOG = logging.getLogger(__name__)


class Resource(object):

    __slots__ = ('queue_ctrl')

    def __init__(self, queue_controller):
        self.queue_ctrl = queue_controller

    def on_get(self, req, resp, project_id, queue_name):
        try:
            resp_dict = self.queue_ctrl.stats(queue_name,
                                              project=project_id)

            message_stats = resp_dict['messages']

            if message_stats['total'] != 0:
                base_path = req.path[:req.path.rindex('/')] + '/messages/'

                newest = message_stats['newest']
                newest['href'] = base_path + newest['id']
                del newest['id']

                oldest = message_stats['oldest']
                oldest['href'] = base_path + oldest['id']
                del oldest['id']

            resp.content_location = req.path
            resp.body = utils.to_json(resp_dict)
            # status defaults to 200

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise falcon.HTTPNotFound()

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Queue stats could not be read.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

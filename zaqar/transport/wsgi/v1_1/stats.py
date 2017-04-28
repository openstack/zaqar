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

from oslo_log import log as logging
import six

from zaqar.i18n import _
from zaqar.storage import errors as storage_errors
from zaqar.transport import utils
from zaqar.transport.wsgi import errors as wsgi_errors


LOG = logging.getLogger(__name__)


class Resource(object):

    __slots__ = '_queue_ctrl'

    def __init__(self, queue_controller):
        self._queue_ctrl = queue_controller

    def on_get(self, req, resp, project_id, queue_name):
        try:
            resp_dict = self._queue_ctrl.stats(queue_name,
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

            resp.body = utils.to_json(resp_dict)
            # status defaults to 200

        except (storage_errors.QueueDoesNotExist,
                storage_errors.QueueIsEmpty) as ex:
            resp_dict = {
                'messages': {
                    'claimed': 0,
                    'free': 0,
                    'total': 0
                }
            }
            resp.body = utils.to_json(resp_dict)

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(six.text_type(ex))

        except Exception as ex:
            LOG.exception(ex)
            description = _(u'Queue stats could not be read.')
            raise wsgi_errors.HTTPServiceUnavailable(description)

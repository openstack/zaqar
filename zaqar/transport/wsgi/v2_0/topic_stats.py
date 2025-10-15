# Copyright (c) 2019 Rackspace, Inc.
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

from zaqar.common import decorators
from zaqar.i18n import _
from zaqar.storage import errors as storage_errors
from zaqar.transport import acl
from zaqar.transport import utils
from zaqar.transport.wsgi import errors as wsgi_errors


LOG = logging.getLogger(__name__)


class Resource:

    __slots__ = '_topic_ctrl'

    def __init__(self, topic_controller):
        self._topic_ctrl = topic_controller

    @decorators.TransportLog("Topics stats item")
    @acl.enforce("topics:stats")
    def on_get(self, req, resp, project_id, topic_name):
        try:
            resp_dict = self._topic_ctrl.stats(topic_name,
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

            resp.text = utils.to_json(resp_dict)
            # status defaults to 200

        except (storage_errors.TopicDoesNotExist,
                storage_errors.TopicIsEmpty):
            resp_dict = {
                'messages': {
                    'claimed': 0,
                    'free': 0,
                    'total': 0
                }
            }
            resp.text = utils.to_json(resp_dict)

        except storage_errors.DoesNotExist as ex:
            LOG.debug(ex)
            raise wsgi_errors.HTTPNotFound(str(ex))

        except Exception:
            description = _('Topic stats could not be read.')
            LOG.exception(description)
            raise wsgi_errors.HTTPServiceUnavailable(description)

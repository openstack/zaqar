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

from six.moves import urllib

from keystoneauth1.identity import v3
from keystoneauth1 import session as keystone_session
from oslo_log import log as logging
import swiftclient

from zaqar.common import decorators
from zaqar import storage
from zaqar.storage.swift import controllers
from zaqar.storage.swift import options

LOG = logging.getLogger(__name__)


class DataDriver(storage.DataDriverBase):

    _DRIVER_OPTIONS = options._config_options()

    def __init__(self, conf, cache, control_driver):
        super(DataDriver, self).__init__(conf, cache, control_driver)
        self.swift_conf = self.conf[options.MESSAGE_SWIFT_GROUP]

    @property
    def capabilities(self):
        return (
            storage.Capabilities.AOD,
            storage.Capabilities.DURABILITY,
        )

    @decorators.lazy_property(write=False)
    def connection(self):
        return _ClientWrapper(self.swift_conf)

    def is_alive(self):
        return True

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        return controllers.QueueController(self)

    @decorators.lazy_property(write=False)
    def message_controller(self):
        return controllers.MessageController(self)

    @decorators.lazy_property(write=False)
    def subscription_controller(self):
        return controllers.SubscriptionController(self)

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        return controllers.ClaimController(self)

    def _health(self):
        raise NotImplementedError("No health checks")

    def close(self):
        pass


class _ClientWrapper(object):
    """Wrapper around swiftclient.Connection.

    This wraps swiftclient.Connection to give the same API, but provide a
    thread-safe alternative with a different object for every method call. It
    maintains performance by managing authentication itself, and passing the
    token afterwards.
    """

    def __init__(self, conf):
        self.conf = conf
        self.parsed_url = urllib.parse.urlparse(conf.uri)
        self.token = None
        self.url = None
        self.session = None
        self.auth = None

    def _refresh_auth(self):
        self.auth = v3.Password(
            username=self.parsed_url.username,
            password=self.parsed_url.password,
            project_name=self.parsed_url.path[1:],
            user_domain_id=self.conf.user_domain_id,
            user_domain_name=self.conf.user_domain_name,
            project_domain_id=self.conf.project_domain_id,
            project_domain_name=self.conf.project_domain_name,
            auth_url=self.conf.auth_url)
        self.session = keystone_session.Session(auth=self.auth)
        self.url = self.session.get_endpoint(service_type='object-store')
        self.token = self.session.get_token()

    def __getattr__(self, attr):
        # This part is not thread-safe, but the worst case is having a bunch of
        # useless auth calls, so it should be okay.
        if (self.auth is None or
                self.auth.get_auth_ref(self.session).will_expire_soon()):
            self._refresh_auth()
        client = swiftclient.Connection(
            preauthurl=self.url,
            preauthtoken=self.token,
            insecure=self.conf.insecure)
        return getattr(client, attr)

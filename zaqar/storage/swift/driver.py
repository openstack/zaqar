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

import logging
from osprofiler import profiler
import urllib

from keystoneauth1.identity import generic
from keystoneauth1 import session as keystone_session
from oslo_log import log as oslo_logging
import swiftclient

from zaqar.common import decorators
from zaqar.conf import drivers_message_store_swift
from zaqar import storage
from zaqar.storage.swift import controllers

LOG = oslo_logging.getLogger(__name__)


class DataDriver(storage.DataDriverBase):

    _DRIVER_OPTIONS = [(drivers_message_store_swift.GROUP_NAME,
                        drivers_message_store_swift.ALL_OPTS)]

    def __init__(self, conf, cache, control_driver):
        super().__init__(conf, cache, control_driver)
        self.swift_conf = self.conf[drivers_message_store_swift.GROUP_NAME]
        if not self.conf.debug:
            # Reduce swiftclient logging, in particular to remove 404s
            logging.getLogger("swiftclient").setLevel(logging.WARNING)

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
        try:
            self.connection.get_capabilities()
            return True
        except Exception:
            LOG.exception('Aliveness check failed:')
            return False

    @decorators.lazy_property(write=False)
    def message_controller(self):
        controller = controllers.MessageController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            return profiler.trace_cls("swift_message_controller")(controller)
        else:
            return controller

    @decorators.lazy_property(write=False)
    def subscription_controller(self):
        controller = controllers.SubscriptionController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            return profiler.trace_cls("swift_subscription_"
                                      "controller")(controller)
        else:
            return controller

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        controller = controllers.ClaimController(self)
        if (self.conf.profiler.enabled and
                self.conf.profiler.trace_message_store):
            return profiler.trace_cls("swift_claim_controller")(controller)
        else:
            return controller

    def _health(self):
        raise NotImplementedError("No health checks")

    def close(self):
        pass


class _ClientWrapper:
    """Wrapper around swiftclient.Connection.

    This wraps swiftclient.Connection to give the same API, but provide a
    thread-safe alternative with a different object for every method call. It
    maintains performance by managing authentication itself, and passing the
    token afterwards.
    """

    def __init__(self, conf):
        self.conf = conf
        self.endpoint = None
        self.parsed_url = urllib.parse.urlparse(conf.uri)
        self.session = None

    def _init_auth(self):
        auth = generic.Password(
            username=self.parsed_url.username,
            password=self.parsed_url.password,
            project_name=self.parsed_url.path[1:],
            user_domain_id=self.conf.user_domain_id,
            user_domain_name=self.conf.user_domain_name,
            project_domain_id=self.conf.project_domain_id,
            project_domain_name=self.conf.project_domain_name,
            auth_url=self.conf.auth_url)
        self.session = keystone_session.Session(auth=auth)
        self.endpoint = self.session.get_endpoint(
            service_type='object-store',
            interface=self.conf.interface,
            region_name=self.conf.region_name
        )

    def __getattr__(self, attr):
        if self.session is None:
            self._init_auth()
        os_options = {
            'object_storage_url': self.endpoint
        }
        client = swiftclient.Connection(session=self.session,
                                        insecure=self.conf.insecure,
                                        os_options=os_options)
        return getattr(client, attr)

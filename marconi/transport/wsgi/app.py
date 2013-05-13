# Copyright (c) 2013 Red Hat, Inc.
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
"""
Gunicorn Application implementation for Marconi
"""

import gunicorn.app.base as gunicorn
import gunicorn.config as gconfig

from marconi.common import config
import marconi.openstack.common.log as logging


OPTIONS = {
    # Process
    "user": None,
    "group": None,
    "proc_name": "marconi",

    # SSL
    "certfile": None,
    "keyfile": None,

    # Network
    "workers": 1,
    "bind": "0.0.0.0:8888",
    "worker_class": "sync"
}

cfg = config.namespace('drivers:transport:wsgi').from_options(**OPTIONS)

LOG = logging.getLogger(__name__)


class Application(gunicorn.Application):

    def __init__(self, wsgi_app, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        self.app = wsgi_app

    def load(self):
        return self.app

    def load_config(self):
        self.cfg = gconfig.Config(self.usage, prog=self.prog)

        for key in OPTIONS:
            self.cfg.set(key, getattr(cfg, key))

        self.logger = LOG

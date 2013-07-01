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

import ConfigParser
import os
import uuid


class Config(object):
    def __init__(self, config_path=None):
        if config_path is None:
            if os.path.exists('/etc/marconi/system-tests.conf'):
                config_path = '/etc/marconi/system-tests.conf'
            else:
                config_path = os.path.expanduser('~/.marconi'
                                                 '/system-tests.conf')
        self.parser = ConfigParser.SafeConfigParser()
        self.parser.read(config_path)

    @property
    def auth_enabled(self):
        return self.parser.getboolean('auth', 'auth_on')

    @property
    def username(self):
        return self.parser.get('auth', 'username')

    @property
    def password(self):
        return self.parser.get('auth', 'password')

    @property
    def auth_url(self):
        return self.parser.get('auth', 'url')

    @property
    def base_server(self):
        return self.parser.get('marconi_env', 'marconi_url')

    @property
    def marconi_version(self):
        return self.parser.get('marconi_env', 'marconi_version')

    @property
    def base_url(self):
        return (self.base_server + '/' + self.marconi_version)

    @property
    def uuid(self):
        return str(uuid.uuid1())

    @property
    def user_agent(self):
        return self.parser.get('header_values', 'useragent')

    @property
    def host(self):
        return self.parser.get('header_values', 'host')

    @property
    def project_id(self):
        return self.parser.get('header_values', 'project_id')

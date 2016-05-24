# Copyright (c) 2016 HuaWei, Inc.
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
from oslo_config import cfg


class Configuration(object):

    def __init__(self, conf):
        """Initialize configuration."""
        self.local_conf = conf

    def register_opts(self, volume_opts, group=None):
        self.local_conf.register_opts(volume_opts, group=group)

    def set_override(self, name, override, group=None, enforce_type=False):
        self.local_conf.set_override(name, override, group=group,
                                     enforce_type=enforce_type)

    def safe_get(self, value):
        try:
            return self.__getattr__(value)
        except cfg.NoSuchOptError:
            return None

    def __contains__(self, key):
        """Return True if key is in local_conf."""
        return key in self.local_conf

    def __getattr__(self, value):
        # Don't use self.local_conf to avoid reentrant call to __getattr__()
        local_conf = object.__getattribute__(self, 'local_conf')
        return getattr(local_conf, value)

    def __getitem__(self, key):
        """Look up an option value and perform string substitution."""
        return self.local_conf.__getitem__(key)

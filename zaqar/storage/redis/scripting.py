# Copyright (c) 2014 Rackspace Hosting, Inc.
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

import os

from zaqar.common import decorators


class Mixin(object):
    script_names = []

    @decorators.lazy_property(write=False)
    def _scripts(self):
        scripts = {}

        for name in self.script_names:
            script = _read_script(name)
            scripts[name] = self._client.register_script(script)

        return scripts


def _read_script(script_name):
    folder = os.path.abspath(os.path.dirname(__file__))
    filename = os.path.join(folder, 'scripts', script_name + '.lua')

    with open(filename, 'r') as script_file:
        return script_file.read()

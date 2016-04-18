# Copyright (c) 2016 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import os

from tempest.test_discover import plugins

from zaqar.tests.tempest_plugin import config as zaqar_config


class ZaqarTempestPlugin(plugins.TempestPlugin):
    def load_tests(self):
        base_path = os.path.split(os.path.dirname(
            os.path.abspath(__file__)))[0]
        # Note: base_path should be set to the top directory
        # of zaqar.
        base_path += '/../..'
        test_dir = "zaqar/tests/tempest_plugin/tests"
        full_test_dir = os.path.join(base_path, test_dir)
        return full_test_dir, base_path

    def register_opts(self, conf):
        conf.register_group(zaqar_config.messaging_group)
        conf.register_opts(zaqar_config.MessagingGroup, group='messaging')
        conf.register_opt(zaqar_config.service_option,
                          group='service_available')

    def get_opt_lists(self):
        return [('messaging', zaqar_config.MessagingGroup),
                ('service_available', [zaqar_config.service_option])]

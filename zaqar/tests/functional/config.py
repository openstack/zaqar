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

import os

from oslo_config import cfg
from oslo_log import log


_DEFAULT = (
    cfg.BoolOpt("run_tests", default=True),
)


_ZAQAR_OPTIONS = (
    cfg.StrOpt("url", default="http://127.0.0.1:8888"),
    cfg.StrOpt("config", default="functional-zaqar.conf"),
)


_HEADERS_OPTIONS = (
    cfg.StrOpt("user_agent", default="FunctionalTests"),
    cfg.StrOpt("project_id", default="123456"),
)


def load_config():
    conf = cfg.ConfigOpts()
    conf.register_opts(_DEFAULT)
    conf.register_opts(_ZAQAR_OPTIONS, group="zaqar")
    conf.register_opts(_HEADERS_OPTIONS, group="headers")

    log.register_options(conf)

    conf_path = os.path.join(os.environ["ZAQAR_TESTS_CONFIGS_DIR"],
                             "functional-tests.conf")
    conf(args=[], default_config_files=[conf_path])
    return conf

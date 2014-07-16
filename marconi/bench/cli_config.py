# Copyright (c) 2014 Rackspace, Inc.
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

from oslo.config import cfg
import psutil

conf = cfg.CONF
_CLI_OPTIONS = (
    cfg.IntOpt(
        'processes',
        short='p',
        default=psutil.NUM_CPUS,
        help='Number of Processes'),
    cfg.IntOpt(
        'workers',
        short='w',
        default=psutil.NUM_CPUS * 2,
        help='Number of Workers'),
    cfg.IntOpt('time', short='t', default=3, help="time in seconds"),
)
conf.register_cli_opts(_CLI_OPTIONS)
conf(project='marconi', prog='marconi-queues')

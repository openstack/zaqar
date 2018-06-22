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

trace_wsgi_transport = cfg.BoolOpt(
    "trace_wsgi_transport", default=False,
    help="If False doesn't trace any transport requests."
         "Please note that it doesn't work for websocket now.")


trace_message_store = cfg.BoolOpt(
    "trace_message_store", default=False,
    help="If False doesn't trace any message store requests.")


trace_management_store = cfg.BoolOpt(
    "trace_management_store", default=False,
    help="If False doesn't trace any management store requests.")


GROUP_NAME = 'profiler'
ALL_OPTS = [
    trace_wsgi_transport,
    trace_message_store,
    trace_management_store
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}

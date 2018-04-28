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

auth_url = cfg.StrOpt(
    "auth_url", default="http://127.0.0.1:5000/v3/",
    help="URI of Keystone endpoint to discover Swift")


uri = cfg.StrOpt(
    "uri",
    default="swift://demo:nomoresecrete@/demo",
    help="Custom URI describing the swift connection.")


insecure = cfg.StrOpt(
    "insecure", default=False,
    help="Don't check SSL certificate")


project_domain_id = cfg.StrOpt(
    "project_domain_id", default="default",
    help="Domain ID containing project")


project_domain_name = cfg.StrOpt(
    "project_domain_name",
    help="Domain name containing project")


user_domain_id = cfg.StrOpt(
    "user_domain_id", default="default",
    help="User's domain id")


user_domain_name = cfg.StrOpt(
    "user_domain_name", help="User's domain name")


region_name = cfg.StrOpt(
    "region_name", help="Region name")


interface = cfg.StrOpt(
    "interface", default="publicURL",
    help="The default interface for endpoint URL "
         "discovery.")


GROUP_NAME = 'drivers:message_store:swift'
ALL_OPTS = [
    auth_url,
    uri,
    insecure,
    project_domain_id,
    project_domain_name,
    user_domain_id,
    user_domain_name,
    region_name,
    interface
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}

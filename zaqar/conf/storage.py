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

from zaqar.i18n import _


queue_pipeline = cfg.ListOpt(
    'queue_pipeline', default=[],
    help=_('Pipeline to use for processing queue operations. This pipeline '
           'will be consumed before calling the storage driver\'s controller '
           'methods.'))


message_pipeline = cfg.ListOpt(
    'message_pipeline', default=[],
    help=_('Pipeline to use for processing message operations. This pipeline '
           'will be consumed before calling the storage driver\'s controller '
           'methods.'))


claim_pipeline = cfg.ListOpt(
    'claim_pipeline', default=[],
    help=_('Pipeline to use for processing claim operations. This pipeline '
           'will be consumed before calling the storage driver\'s controller '
           'methods.'))


subscription_pipeline = cfg.ListOpt(
    'subscription_pipeline', default=[],
    help=_('Pipeline to use for processing subscription operations. This '
           'pipeline will be consumed before calling the storage driver\'s '
           'controller methods.'))


topic_pipeline = cfg.ListOpt(
    'topic_pipeline', default=[],
    help=_('Pipeline to use for processing topic operations. This '
           'pipeline will be consumed before calling the storage driver\'s '
           'controller methods.'))


GROUP_NAME = 'storage'
ALL_OPTS = [
    queue_pipeline,
    message_pipeline,
    claim_pipeline,
    subscription_pipeline,
    topic_pipeline
]


def register_opts(conf):
    conf.register_opts(ALL_OPTS, group=GROUP_NAME)


def list_opts():
    return {GROUP_NAME: ALL_OPTS}

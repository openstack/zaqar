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
#
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo.config import cfg

from marconi import common
from marconi.common import decorators
from marconi.openstack.common import importutils
from marconi.openstack.common import log as logging
from marconi.queues.storage import base

LOG = logging.getLogger(__name__)

_PIPELINE_RESOURCES = ('queue', 'message', 'claim')

_PIPELINE_CONFIGS = [
    cfg.ListOpt(resource + '_pipeline', default=[],
                help=_('Pipeline to use for processing {0} operations. '
                       'This pipeline will be consumed before calling '
                       'the storage driver\'s controller methods, '
                       'which will always be appended to this '
                       'pipeline.').format(resource))
    for resource in _PIPELINE_RESOURCES
]

_PIPELINE_GROUP = 'storage'


def _get_storage_pipeline(resource_name, conf):
    """Constructs and returns a storage resource pipeline.

    This is a helper function for any service supporting
    pipelines for the storage layer. The function returns
    a pipeline based on the `{resource_name}_pipeline`
    config option.

    Stages in the pipeline implement controller methods
    that they want to hook. A stage can halt the
    pipeline immediate by returning a value that is
    not None; otherwise, processing will continue
    to the next stage, ending with the actual storage
    controller.

    :param conf: Configuration instance.
    :type conf: `cfg.ConfigOpts`

    :returns: A pipeline to use.
    :rtype: `Pipeline`
    """
    conf.register_opts(_PIPELINE_CONFIGS,
                       group=_PIPELINE_GROUP)

    storage_conf = conf[_PIPELINE_GROUP]

    pipeline = []
    for ns in storage_conf[resource_name + '_pipeline']:
        cls = importutils.try_import(ns)

        if not cls:
            msg = _('Pipe {0} could not be imported').format(ns)
            LOG.warning(msg)
            continue

        pipeline.append(cls())

    return common.Pipeline(pipeline)


class Driver(base.DriverBase):
    """Meta-driver for injecting pipelines in front of controllers.

    :param conf: Configuration from which to load pipeline settings
    :param storage: Storage driver that will service requests as the
        last step in the pipeline
    """

    def __init__(self, conf, storage):
        self._conf = conf
        self._storage = storage

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        pipes = _get_storage_pipeline('queue', self._conf)
        pipes.append(self._storage.queue_controller)
        return pipes

    @decorators.lazy_property(write=False)
    def message_controller(self):
        pipes = _get_storage_pipeline('message', self._conf)
        pipes.append(self._storage.message_controller)
        return pipes

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        pipes = _get_storage_pipeline('claim', self._conf)
        pipes.append(self._storage.claim_controller)
        return pipes

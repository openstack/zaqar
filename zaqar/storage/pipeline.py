# Copyright (c) 2013 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

from oslo_config import cfg
from oslo_log import log as logging
from osprofiler import profiler
from stevedore import driver
from stevedore import extension

from zaqar import common
from zaqar.common import decorators
from zaqar.i18n import _
from zaqar.storage import base

LOG = logging.getLogger(__name__)

_PIPELINE_RESOURCES = ('queue', 'message', 'claim', 'subscription')

_PIPELINE_CONFIGS = tuple((
    cfg.ListOpt(resource + '_pipeline', default=[],
                help=_('Pipeline to use for processing {0} operations. '
                       'This pipeline will be consumed before calling '
                       'the storage driver\'s controller methods.')
                .format(resource))
    for resource in _PIPELINE_RESOURCES
))

_PIPELINE_GROUP = 'storage'


def _config_options():
    return [(_PIPELINE_GROUP, _PIPELINE_CONFIGS)]


def _get_storage_pipeline(resource_name, conf, *args, **kwargs):
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
        try:
            mgr = driver.DriverManager('zaqar.storage.stages',
                                       ns,
                                       invoke_args=args,
                                       invoke_kwds=kwargs,
                                       invoke_on_load=True)
            pipeline.append(mgr.driver)
        except RuntimeError as exc:
            LOG.warning(u'Stage %(stage)s could not be imported: %(ex)s',
                        {'stage': ns, 'ex': str(exc)})
            continue

    return pipeline


def _get_builtin_entry_points(resource_name, storage, control_driver, conf):
    # Load builtin stages
    builtin_entry_points = []

    # NOTE(flaper87): The namespace will look like:
    # `zaqar.storage.$STORAGE.driver.stages`. For now,
    # the builtin stages are bound to a single store and
    # are not applied to every store.
    namespace = '%s.%s.stages' % (storage.__module__, resource_name)
    extensions = extension.ExtensionManager(namespace,
                                            invoke_on_load=True,
                                            invoke_args=[storage,
                                                         control_driver])

    if len(extensions.extensions) == 0:
        return []

    for ext in extensions.extensions:
        builtin_entry_points.append(ext.obj)
    if conf.profiler.enabled and conf.profiler.trace_message_store:
        return (profiler.trace_cls("stages_controller")
                (builtin_entry_points))
    return builtin_entry_points


class DataDriver(base.DataDriverBase):
    """Meta-driver for injecting pipelines in front of controllers.

    :param conf: Configuration from which to load pipeline settings
    :param storage: Storage driver that will service requests as the
        last step in the pipeline
    """

    def __init__(self, conf, storage, control_driver):
        # NOTE(kgriffs): Pass None for cache since it won't ever
        # be referenced.
        super(DataDriver, self).__init__(conf, None, control_driver)
        self._storage = storage

    @property
    def capabilities(self):
        return self._storage.capabilities()

    def close(self):
        self._storage.close()

    def is_alive(self):
        return self._storage.is_alive()

    def _health(self):
        return self._storage._health()

    @decorators.lazy_property(write=False)
    def queue_controller(self):
        stages = _get_builtin_entry_points('queue', self._storage,
                                           self.control_driver, self.conf)
        stages.extend(_get_storage_pipeline('queue', self.conf))
        stages.append(self._storage.queue_controller)
        return common.Pipeline(stages)

    @decorators.lazy_property(write=False)
    def message_controller(self):
        stages = _get_builtin_entry_points('message', self._storage,
                                           self.control_driver, self.conf)
        kwargs = {'subscription_controller':
                  self._storage.subscription_controller,
                  'max_notifier_workers':
                  self.conf.notification.max_notifier_workers,
                  'require_confirmation':
                  self.conf.notification.require_confirmation,
                  'queue_controller':
                  self._storage.queue_controller}
        stages.extend(_get_storage_pipeline('message', self.conf, **kwargs))
        stages.append(self._storage.message_controller)
        return common.Pipeline(stages)

    @decorators.lazy_property(write=False)
    def claim_controller(self):
        stages = _get_builtin_entry_points('claim', self._storage,
                                           self.control_driver, self.conf)
        stages.extend(_get_storage_pipeline('claim', self.conf))
        stages.append(self._storage.claim_controller)
        return common.Pipeline(stages)

    @decorators.lazy_property(write=False)
    def subscription_controller(self):
        stages = _get_builtin_entry_points('subscription', self._storage,
                                           self.control_driver, self.conf)
        stages.extend(_get_storage_pipeline('subscription', self.conf))
        stages.append(self._storage.subscription_controller)
        return common.Pipeline(stages)

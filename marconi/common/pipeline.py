# Copyright (c) 2013 Red Hat, Inc.
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

"""This module implements a common Pipeline object.

The pipeline can be used to enhance the storage layer with filtering, routing,
multiplexing and the like. For example:

    >>> pipes = [MessageFiltering(), ShardManager(), QueueController()]
    >>> pipeline = Pipeline(pipes)
    >>> pipeline.create(...)

Every pipe has to implement the method it wants to hook into. This method
will be called when the pipeline consumption gets to that point - pipes
ordering matters - and will continue unless the method call returns a value
that is not None.

At least one of the pipes has to implement the calling method. If none of
them do, an AttributeError exception will be raised.

Other helper functions can also be found in this module. `get_storage_pipeline`
for example, creates a pipeline based on the `storage_pipeline` configuration
option. This config is a ListOpt and can be either set programmatically or in
the configuration file itself:

    [storage]
    storage_pipeline = marconi.queues.storage.filters.ValidationFilter,
                       marconi.queues.storage.sharding.ShardManager

Note that controllers *must* not be present in this configuration option.
They will be loaded - and automatically appended to the pipeline - using
the `drivers:storage` configuration parameter.
"""

import functools

from oslo.config import cfg
import six

from marconi.openstack.common import importutils
import marconi.openstack.common.log as logging

LOG = logging.getLogger(__name__)

_PIPELINE_CONFIGS = [
    cfg.ListOpt('storage_pipeline', default=[],
                help=_('Pipeline to use for the storage layer '
                       'This pipeline will be consumed before '
                       'calling the controller method, which will '
                       'always be appended to this pipeline'))
]


def get_storage_pipeline(conf):
    """Returns a pipeline based on `storage_pipeline`

    This is a helper function for any service supporting
    pipelines for the storage layer - Proxy and Queues,
    for example. The function returns a pipeline based on
    the `storage_pipeline` config option.

    :param conf: Configuration instance.
    :param conf: `cfg.ConfigOpts`

    :returns: A pipeline to use.
    :rtype: `Pipeline`
    """
    conf.register_opts(_PIPELINE_CONFIGS,
                       group='storage')

    pipeline = []
    for ns in conf.storage.storage_pipeline:
        cls = importutils.try_import(ns)

        if not cls:
            msg = _('Pipe {0} could not be imported').format(ns)
            LOG.warning(msg)
            continue

        pipeline.append(cls())

    return Pipeline(pipeline)


class Pipeline(object):

    def __init__(self, pipeline=None):
        self._pipeline = pipeline and list(pipeline) or []

    def append(self, item):
        self._pipeline.append(item)

    def __getattr__(self, name):
        return functools.partial(self.consume_for, name)

    def consume_for(self, method, *args, **kwargs):
        """Consumes the pipeline for `method`

        This method walks through the pipeline and calls
        `method` for each of the items in the pipeline. A
        warning will be logged for each pipe not implementing
        `method` and an Attribute error will be raised if
        none of the pipes do.

        :params method: The method name to call on each pipe
        :type method: `six.text_type`
        :param args: Positional arguments to pass to the call.
        :param kwargs: Keyword arguments to pass to the call.

        :returns: Anything returned by the called methods.
        :raises: AttributeError if none of the pipes implement `method`
        """
        # NOTE(flaper87): Used as a way to verify
        # the requested method exists in at least
        # one of the pipes, otherwise AttributeError
        # will be raised.
        target = None

        for pipe in self._pipeline:
            try:
                target = getattr(pipe, method)
            except AttributeError:
                spipe = six.text_type(pipe)
                msg = _(u"Pipe {0} does not implement {1}").format(spipe,
                                                                   method)
                LOG.warning(msg)
                continue

            result = target(*args, **kwargs)

            # NOTE(flaper87): Will keep going forward
            # through the pipeline unless the call returns
            # something.
            if result is not None:
                return result

        if target is None:
            msg = _(u'Method {0} not found in any of '
                    'the registered pipes').format(method)
            LOG.error(msg)
            raise AttributeError(msg)

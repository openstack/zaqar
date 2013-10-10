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

import functools

import six

import marconi.openstack.common.log as logging

LOG = logging.getLogger(__name__)


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

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

"""WSGI App for WSGI Containers

This app should be used by external WSGI
containers. For example:

    $ gunicorn zaqar.transport.wsgi.app:app

NOTE: As for external containers, it is necessary
to put config files in the standard paths. There's
no common way to specify / pass configuration files
to the WSGI app when it is called from other apps.
"""

from oslo_config import cfg

from zaqar import bootstrap

# TODO(kgriffs): For now, we have to use the global config
# to pick up common options from openstack.common.log, since
# that module uses the global CONF instance exclusively.
conf = cfg.CONF
conf(project='zaqar', prog='zaqar-queues', args=[])

boot = bootstrap.Bootstrap(conf)
conf.drivers.transport = 'wsgi'
app = boot.transport.app

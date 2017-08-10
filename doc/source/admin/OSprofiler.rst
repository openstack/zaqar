..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

================
OSprofiler Guide
================

OSprofiler is a library from oslo. It's used for performance analysis. Please
see `Official Doc`_ for more detail.

Preparation
-----------
OSprofiler now supports some kind of backends, such as Ceilometer, ElasticSearch
, Messaging and MongoDB.

.. note:: 1. Ceilometer is only used for data collection, and Messaging is only
   used for data transfer. So Ceilometer only works when Messaging is enabled.
   2. ElasticSearch and MongoDB support both data collection and transfer. So
   they can be used standalone.

In this guide, we take MongoDB for example.

There are some new config options.

**enabled**

Enables the profiling for all services on this node. Default value is False
(fully disable the profiling feature). This function may bring down Zaqar's
performance, so please set to disable in production environment.

**connection_string**

Connection string for a notifier backend. Default value is messaging:// which
sets the notifier to oslo_messaging. Here we set it to
"mongodb://localhost:27017"

**hmac_keys**

Secret key(s) to use for encrypting context data for performance profiling.
This string value should have the following format: <key1>[,<key2>,...<keyn>],
where each key is some random string. A user who triggers the profiling via
the REST API has to set one of these keys in the headers of the REST API call
to include profiling results of this node for this particular project.

**trace_wsgi_transport**, **trace_message_store** and **trace_management_store**

The three layers during a user's request flow. Set to True to enable tracing
for each layer.

So In this example, we should add the following config options::

    [profiler]
    enabled = True
    connection_string = mongodb://localhost:27017
    hmac_keys = 123
    trace_wsgi_transport = True
    trace_message_store = True
    trace_management_store = True

.. note:: If you want to use MQ and Ceilometer, please leave the
   **connection_string** empty or indicate the MQ information. And please make
   sure that the following config options have be set in Ceilometer.conf

::

    [DEFAULT]
    event_dispatchers = database

    [oslo_messaging_notifications]
    topics = notifications, profiler

Then restart Zaqar service

Command Line
------------

we can use OpenStack Client to analyse the user request now. For example, if we
want to know the performance for "queue list", we can do like this:

1. OpenStack Client now supports OSprofiler by default. Only thing we need to
do is adding ``--os-profile {hmac_keys}`` in the command::

    openstack queue list --os-profile 123

"123" here is what we set in Zaqar config file. After the request is done,
OpenStack Client will return a trace ID like::

    Trace ID: 2902c7a3-ee18-4b08-aae7-4e34388f9352
    Display trace with command:
    osprofiler trace show --html 2902c7a3-ee18-4b08-aae7-4e34388f9352

Now the trace information has been stored in MongoDB already.

2. Use the command from the openstack client return information. The osprofiler
command uses Ceilometer for data collection by default, so we need use
``--connection-string`` to change it to mongoDB here::

    osprofiler trace show --html 2902c7a3-ee18-4b08-aae7-4e34388f9352 --connection-string mongodb://localhost:27017

Then you can see the analysis information in html format now.

It also supports json format::

    osprofiler trace show --json 2902c7a3-ee18-4b08-aae7-4e34388f9352 --connection-string mongodb://localhost:27017

Of course it supports to save the result to a file::

    osprofiler trace show --json 2902c7a3-ee18-4b08-aae7-4e34388f9352 --out list_test --connection-string mongodb://localhost:27017

Then you can open the file "list_test" to get the result.

.. note:: If you used MQ for data transfer, the "--connection-string" here
   could be ignored or set it to your Ceilometer endpoint.

.. _Official Doc: https://docs.openstack.org/osprofiler/latest/user/background.html

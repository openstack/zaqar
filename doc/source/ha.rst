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

Minimum Scalable HA Setup
=========================

OpenStack Queuing Service has two main layers. First one is the transport
(queuing application) layer which provides the RESTful interface, second one
is the storage layer which keeps all the data and meta-data about queues and messages.

For a HA setup, a load balancer has to be placed in front of the web servers.
Load balancer setup is out of scope in this document.

For storage we will use ``mongoDB`` in order to provide high availability with
minimum administration overhead. For transport, we will use ``wsgi``.

To have a small footprint while providing HA, we will use 2 web servers which
will host the application and 3 mongoDB servers (configured as replica-sets)
which will host the catalog and queues databases. At larger scale, catalog
database and the queues database are advised to be hosted on different mongoDB replica sets.

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

=====================================
Welcome to the Zaqar's Documentation!
=====================================

Zaqar is a multi-tenant cloud messaging and notification service for web
and mobile developers.

The service features a REST API, which developers can use to send messages
between various components of their SaaS and mobile applications, by using a
variety of communication patterns. Underlying this API is an efficient
messaging engine designed with scalability and security in mind. The Websocket
API is also available.

Other OpenStack components can integrate with Zaqar to surface events to end
users and to communicate with guest agents that run in the "over-cloud" layer.

Key features
------------

Zaqar provides the following key features:

* Choice between two communication transports. Both with Keystone support:

  * Firewall-friendly, **HTTP-based RESTful API**. Many of today's developers
    prefer a more web-friendly HTTP API. They value the simplicity and
    transparency of the protocol, it's firewall-friendly nature, and it's huge
    ecosystem of tools, load balancers and proxies. In addition, cloud
    operators appreciate the scalability aspects of the REST architectural
    style.
  * **Websocket-based API** for persistent connections. Websocket protocol
    provides communication over persistent connections. Unlike HTTP, where
    new connections are opened for each request/response pair, Websocket can
    transfer multiple requests/responses over single TCP connection. It saves
    much network traffic and minimizes delays.

* Multi-tenant queues based on Keystone project IDs.
* Support for several common patterns including event broadcasting, task
  distribution, and point-to-point messaging.
* Component-based architecture with support for custom backends and message
  filters.
* Efficient reference implementation with an eye toward low latency and high
  throughput (dependent on backend).
* Highly-available and horizontally scalable.
* Support for subscriptions to queues. Several notification types are
  available:

  * Email notifications.
  * Webhook notifications.
  * Websocket notifications.

Project scope
-------------

The Zaqar API is data-oriented. That is, it does not provision message brokers
and expose those directly to clients. Instead, the API acts as a bridge between
the client and one or more backends. A provisioning service for message
brokers, however useful, serves a somewhat different market from what Zaqar is
targeting today. With that in mind, if users are interested in a broker
provisioning service, the community should consider starting a new project to
address that need.

Design principles
-----------------

Zaqar, as with all OpenStack projects, is designed with the following
guidelines in mind:

* **Component-based architecture.** Quickly add new behaviors
* **Highly available and scalable.** Scale to very serious workloads
* **Fault tolerant.** Isolated processes avoid cascading failures
* **Recoverable.** Failures should be easy to diagnose, debug, and rectify
* **Open standards.** Be a reference implementation for a community-driven

Contents
--------
.. toctree::
   :maxdepth: 2

   user/index
   admin/index
   install/index
   configuration/index
   contributor/contributing
   contributor/index
   cli/index

.. toctree::
   :maxdepth: 1

   glossary









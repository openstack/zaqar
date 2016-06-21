==========================
Messaging service overview
==========================

The Message service is multi-tenant, fast, reliable, and scalable. It allows
developers to share data between distributed application components performing
different tasks, without losing messages or requiring each component to be
always available.

The service features a RESTful API and a Websocket API, which developers can
use to send messages between various components of their SaaS and mobile
applications, by using a variety of communication patterns.

Key features
~~~~~~~~~~~~

The Messaging service provides the following key features:

* Choice between two communication transports. Both with Identity service
  support:

  * Firewall-friendly, **HTTP-based RESTful API**. Many of today's developers
    prefer a more web-friendly HTTP API. They value the simplicity and
    transparency of the protocol, its firewall-friendly nature, and its huge
    ecosystem of tools, load balancers and proxies. In addition, cloud
    operators appreciate the scalability aspects of the REST architectural
    style.
  * **Websocket-based API** for persistent connections. Websocket protocol
    provides communication over persistent connections. Unlike HTTP, where
    new connections are opened for each request/response pair, Websocket can
    transfer multiple requests/responses over single TCP connection. It saves
    much network traffic and minimizes delays.

* Multi-tenant queues based on Identity service IDs.
* Support for several common patterns including event broadcasting, task
  distribution, and point-to-point messaging.
* Component-based architecture with support for custom back ends and message
  filters.
* Efficient reference implementation with an eye toward low latency and high
  throughput (dependent on back end).
* Highly-available and horizontally scalable.
* Support for subscriptions to queues. Several notification types are
  available:

  * Email notifications
  * Webhook notifications
  * Websocket notifications

Layers of the Messaging service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Messaging service has following layers:

* The transport layer (Messaging application) which can provide these APIs:

  * HTTP RESTful API (via ``wsgi`` driver).
  * Websocket API (via ``websocket`` driver).

* The storage layer which keeps all the data and metadata about queues and
  messages. It has two sub-layers:

  * The management store database (Catalog). Can be ``MongoDB`` database (or
    ``MongoDB`` replica-set) or SQL database.
  * The message store databases (Pools). Can be ``MongoDB`` database (or
    ``MongoDB`` replica-set) or ``Redis`` database.

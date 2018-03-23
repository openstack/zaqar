===============
Health (health)
===============
With health API, user or operator can get a general idea about the status of
Zaqar server. Those information can be used for basic validation, performance
checking, etc.

Ping
====

.. rest_method::  GET /v2/ping

Simple health check for end user.

A request to ping Zaqar server when server is working returns 204, otherwise
returns 503. This can be a handy API for end user to check if the messaging
service is in working status.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 503


This operation does not accept a request body and does not return a response
body.


Health
======

.. rest_method::  GET /v2/health

Detailed health check for cloud operator/admin.

This is an ``admin only`` API. A request to get detailed health information
of Zaqar server.

The response body will depend on the storage setting of Zaqar server. By
default, there is no pool created. Then the response body will only
contain the ``catalog_reachable``. Otherwise, the response body will have
``catalog_reachable`` and the health status for each pool.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 503


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - catalog_reachable: catalog_reachable
  - storage_reachable: storage_reachable
  - operation_status: operation_status


Response Example
----------------

.. literalinclude:: samples/health-response.json
   :language: javascript


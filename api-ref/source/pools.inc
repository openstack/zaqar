===============
Pools (pools)
===============
If pooling is enabled, queuing service uses multiple queues databases in order
to scale horizontally. A pool (queues database) can be added any time without
stopping the service. Each pool has a weight that is assigned during the
creation time but can be changed later. Pooling is done by queue which
indicates that all messages for a particular queue can be found in the same
pool (queues database).

List pools
==========

.. rest_method:: GET /v2/pools

Lists pools.

This operation lists pools for the project. The pools are sorted
alphabetically by name.


Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 404
   - 401

Query Parameters
-----------------

.. rest_parameters:: parameters.yaml

  - limit: limit
  - marker: marker
  - detailed: detailed

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - pools: pools
  - links: pool_links


Response Example
----------------

.. literalinclude:: samples/pool-list-response.json
   :language: javascript


Create pool
============

.. rest_method:: PUT /v2/pools/{pool_name}

Creates a pool.

This operation creates a new pool.

``pool_name`` is the name that you give to the pool. The name must not
exceed 64 bytes in length, and it is limited to US-ASCII letters, digits,
underscores, and hyphens.


Response codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 409


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - pool_name: pool_name_path
  - weight: pool_weight
  - uri: pool_uri
  - group: pool_group
  - options: pool_options

Request Example
---------------

.. literalinclude:: samples/pool-create-request.json
   :language: javascript


This operation does not return a response body.


Update pool
============

.. rest_method:: PATCH /v2/pools/{pool_name}

Updates a pool.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 404
   - 503


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - pool_name: pool_name_path
  - weight: pool_weight
  - uri: pool_uri
  - group: pool_group
  - options: pool_options


Request Example
---------------

.. literalinclude:: samples/pool-update-request.json
   :language: javascript


Response Example
----------------

.. literalinclude:: samples/pool-update-response.json
   :language: javascript


Show pool details
==================

.. rest_method:: GET /v2/pools/{pool_name}

Shows details for a pool.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - pool_name: pool_name_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - name: pool_name
  - weight: pool_weight
  - uri: pool_uri
  - group: pool_group
  - href: pool_href

Response Example
----------------

.. literalinclude:: samples/pool-show-response.json
   :language: javascript


Delete pool
===============

.. rest_method:: DELETE /v2/pools/{pool_name}

Deletes the specified pool.

This operation immediately deletes a pool.

``pool_name`` is the name that you give to the pool. The name must not
exceed 64 bytes in length, and it is limited to US-ASCII letters, digits,
underscores, and hyphens.


Response codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 503


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - pool_name: pool_name_path

This operation does not accept a request body and does not return a response
body.

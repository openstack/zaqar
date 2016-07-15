===============
Pools (pools)
===============

List pools
===========

.. rest_method:: GET /v2/pools

Lists pools.

This operation lists pools for the project. The pools are sorted
alphabetically by name.


Normal response codes: 200

Error response codes:

- Not Found (404)
- Unauthorized (401)

Query Parameters
-----------------

.. rest_parameters:: parameters.yaml

  - limit: limit
  - marker: marker

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


Normal response codes: 201

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- Conflict (409)


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

Normal response codes: 200

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- Not Found (404)
- ServiceUnavailable (503)


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

Normal response codes: 200

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- ServiceUnavailable (503)

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


Normal response codes: 204

Error response codes:

- Unauthorized (401)
- Forbidden (403)
- ServiceUnavailable (503)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - pool_name: pool_name_path

This operation does not accept a request body and does not return a response
body.

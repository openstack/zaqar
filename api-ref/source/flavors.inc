================
Flavors (flavors)
================
Queue flavors allow users to have different types of queues based on the
storage capabilities. By using flavors, it's possible to allow consumers of the
service to choos between durable storage, fast storage, etc. Flavors must be
created by service administrators and they rely on the existence of pools.

List flavors
============

.. rest_method::  GET /v2/flavors

Lists flavors.

This operation lists flavors for the project. The flavors are sorted
alphabetically by name.


Normal response codes: 200

Error response codes:

- Unauthorized (401)
- Forbidden (403)

Query Parameters
-----------------

.. rest_parameters:: parameters.yaml

  - limit: limit
  - marker: marker

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - flavors: flavors
  - links: flavor_links


Response Example
----------------

.. literalinclude:: samples/flavor-list-response.json
   :language: javascript


Create flavor
=============

.. rest_method::  PUT /v2/flavors/{flavor_name}

Creates a flavor.

This operation creates a new flavor.

``flaovr_name`` is the name that you give to the flavor. The name must not
exceed 64 bytes in length, and it is limited to US-ASCII letters, digits,
underscores, and hyphens.


Normal response codes: 201

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- Forbidden (403)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - flavor_name: flavor_name_path
  - pool_group: flavor_pool_group

Request Example
---------------

.. literalinclude:: samples/flavor-create-request.json
   :language: javascript


This operation does not return a response body.


Update flavor
=============

.. rest_method::  PATCH /v2/flavors/{flavor_name}

Updates a flavor.

Normal response codes: 200

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- Forbidden (403)
- Not Found (404)
- ServiceUnavailable (503)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - flaovr_name: flavor_name_path
  - pool_group: flavor_pool_group


Request Example
---------------

.. literalinclude:: samples/flavor-update-request.json
   :language: javascript


Response Example
----------------

.. literalinclude:: samples/flavor-update-response.json
   :language: javascript


Show flavor details
===================

.. rest_method::  GET /v2/flavors/{flavor_name}

Shows details for a flavor.

Normal response codes: 200

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- Forbidden (403)
- Not Found (404)
- ServiceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - flavor_name: flavor_name_path

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - name: flavor_name
  - capabilities: capabilities
  - pool_group: flavor_pool_group
  - href: flavor_href

Response Example
----------------

.. literalinclude:: samples/flavor-show-response.json
   :language: javascript


Delete flavor
=============

.. rest_method::  DELETE /v2/flavors/{flavor_name}

Deletes the specified flavor.

This operation immediately deletes a flavor.

``flavor_name`` is the name that you give to the flavor. The name must not
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

  - flavor_name: flavor_name_path

This operation does not accept a request body and does not return a response
body.

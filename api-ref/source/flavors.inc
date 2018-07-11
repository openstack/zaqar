=================
Flavors (flavors)
=================

Queue flavors allow users to have different types of queues based on the
storage capabilities. By using flavors, it's possible to allow consumers of the
service to choose between durable storage, fast storage, etc. Flavors must be
created by service administrators and they rely on the existence of pools.

List flavors
============

.. rest_method::  GET /v2/flavors

Lists flavors.

This operation lists flavors for the project. The flavors are sorted
alphabetically by name.


Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403

Query Parameters
-----------------

.. rest_parameters:: parameters.yaml

  - limit: limit
  - marker: marker
  - detailed: detailed

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - flavors: flavors
  - links: flavor_links

Response Example
----------------
NOTE: Suggest config pool_list in stead of pool_group from the
beginning of Queens.

.. literalinclude:: samples/flavor-list-response-new.json
   :language: javascript


Response Example
----------------
NOTE: Remove pool_group in Rocky release and use pool_list instead for pool

.. literalinclude:: samples/flavor-list-response.json
   :language: javascript


Create flavor
=============

.. rest_method::  PUT /v2/flavors/{flavor_name}

Creates a flavor.

This operation creates a new flavor.

``flavor_name`` is the name that you give to the flavor. The name must not
exceed 64 bytes in length, and it is limited to US-ASCII letters, digits,
underscores, and hyphens.


Response codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - flavor_name: flavor_name_path
  - pool_group: flavor_pool_group
  - pool_list: flavor_pool_list

Request Example
---------------
NOTE: Suggest config pool_list in stead of pool_group from the
beginning of Queens.

.. literalinclude:: samples/flavor-create-request-new.json
   :language: javascript


Request Example
---------------
NOTE: Remove pool_group in Rocky release and use pool_list instead for pool

.. literalinclude:: samples/flavor-create-request.json
   :language: javascript


This operation does not return a response body.


Update flavor
=============

.. rest_method::  PATCH /v2/flavors/{flavor_name}

Updates a flavor.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 503


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - flavor_name: flavor_name_path
  - pool_group: flavor_pool_group
  - pool_list: flavor_pool_list

Request Example
---------------
NOTE: Suggest config pool_list in stead of pool_group from the
beginning of Queens.

.. literalinclude:: samples/flavor-update-request-new.json
   :language: javascript


Response Example
----------------
NOTE: Suggest config pool_list in stead of pool_group from the
beginning of Queens.

.. literalinclude:: samples/flavor-update-response-new.json
   :language: javascript


Request Example
---------------
NOTE: Remove pool_group in Rocky release and use pool_list instead for pool

.. literalinclude:: samples/flavor-update-request.json
   :language: javascript


Response Example
----------------
NOTE: Remove pool_group in Rocky release and use pool_list instead for pool

.. literalinclude:: samples/flavor-update-response.json
   :language: javascript


Show flavor details
===================

.. rest_method::  GET /v2/flavors/{flavor_name}

Shows details for a flavor.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 503

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
  - pool_list: flavor_pool_list
  - href: flavor_href

Response Example
----------------
NOTE: Suggest config pool_list in stead of pool_group from the
beginning of Queens.

.. literalinclude:: samples/flavor-show-response-new.json
   :language: javascript


Response Example
----------------
NOTE: Remove pool_group in Rocky release and use pool_list instead for pool

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

  - flavor_name: flavor_name_path

This operation does not accept a request body and does not return a response
body.

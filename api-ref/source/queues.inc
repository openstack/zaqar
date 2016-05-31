===============
Queues (queues)
===============

List queues
===========

.. rest_method::  GET /v2/queues

Lists queues.

A request to list queues when you have no queues in your account returns 204,
instead of 200, because there was no information to send back.

This operation lists queues for the project. The queues are sorted
alphabetically by name.


Normal response codes: 200

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- ServiceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - limit: limit
  - marker: marker

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - queues: queues
  - links: links


Response Example
----------------

.. literalinclude:: samples/queues-list-response.json
   :language: javascript


Create queue
============

.. rest_method::  PUT /v2/queues/{queue_name}

Creates a queue.

This operation creates a new queue.

The body of the request is empty.

``queue_name`` is the name that you give to the queue. The name must not
exceed 64 bytes in length, and it is limited to US-ASCII letters, digits,
underscores, and hyphens.


Normal response codes: 201, 204

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- ServiceUnavailable (503)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name

Request Example
---------------

.. literalinclude:: samples/queue-create-request.json
   :language: javascript


This operation does not return a response body.


Update queue
============

.. rest_method::  PATCH /v2/queues/{queue_name}

Updates a queue.

Normal response codes: 200

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- Not Found (404)
- Conflict (409)
- ServiceUnavailable (503)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name

When setting the request body of updating queue, the body must be a list which
contains a series of json object which follows
https://tools.ietf.org/html/draft-ietf-appsawg-json-patch-10.

.. note::

   - The "Content-Type" header should be
     "application/openstack-messaging-v2.0-json-patch"

   - The ''path'' must start with /metadata, for example, if the key is
     ''ttl'', then the path should be /metadata/ttl


Request Example
---------------

.. literalinclude:: samples/queue-update-request.json
   :language: javascript


Response Example
----------------

.. literalinclude:: samples/queue-update-response.json
   :language: javascript


Show queue details
==================

.. rest_method::  GET /v2/queues/{queue_name}

Shows details for a queue.

Normal response codes: 200

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- ServiceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - _max_messages_post_size: _max_messages_post_size
  - _default_message_ttl: _default_message_ttl

Response Example
----------------

.. literalinclude:: samples/queue-show-response.json
   :language: javascript


Delete queue
===============

.. rest_method::  DELETE /v2/queues/{queue_name}

Deletes the specified queue.

This operation immediately deletes a queue and all of its existing messages.

``queue_name`` is the name that you give to the queue. The name must not
exceed 64 bytes in length, and it is limited to US-ASCII letters, digits,
underscores, and hyphens.


Normal response codes: 204

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- ServiceUnavailable (503)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name

This operation does not accept a request body and does not return a response
body.


Get queue stats
===============

.. rest_method:: GET /v2/queues/{queue_name}/stats

Returns statistics for the specified queue.

This operation returns queue statistics, including how many messages are in
the queue, categorized by status.

If the value of the ``total`` attribute is 0, then ``oldest`` and ``newest``
message statistics are not included in the response.

Normal response codes: 200

Error response codes:

- BadRequest (400)
- Unauthorized (401)
- ServiceUnavailable (503)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name

Response Example
----------------

.. literalinclude:: samples/queue-stats-response.json
   :language: javascript
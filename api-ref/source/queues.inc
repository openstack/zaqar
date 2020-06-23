===============
Queues (queues)
===============
Queue is a logical entity that groups messages. Ideally a queue is created per
work type. For example, if you want to compress files, you would create a queue
dedicated for this job. Any application that reads from this queue would only
compress files.

Nowadays, queue in Zaqar is most like a topic, it's created lazily. User can
post messages to a queue before creating the queue. Zaqar will create the
queue/topic automatically.

List queues
===========

.. rest_method:: GET /v2/queues

Lists queues.

A request to list queues when you have no queues in your account returns 204,
instead of 200, because there was no information to send back.

This operation lists queues for the project. The queues are sorted
alphabetically by name.

When queue listing , we can add filter in query string parameter
to filter queue, like name and metadata. If metadata or name of queue is
consistent with the filter,the queue will be listed to the user,
otherwise the queue will be filtered.

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

  - limit: limit
  - marker: marker
  - detailed: detailed
  - name: name
  - with_count: with_count

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - queues: queues
  - links: links
  - count: count


Response Example
----------------

.. literalinclude:: samples/queues-list-response.json
   :language: javascript


Create queue
============

.. rest_method:: PUT /v2/queues/{queue_name}

Creates a queue.

This operation creates a new queue.

The body of the request is empty.

``queue_name`` is the name that you give to the queue. The name must not
exceed 64 bytes in length, and it is limited to US-ASCII letters, digits,
underscores, and hyphens.

When create queue, user can specify metadata for the queue. Currently, Zaqar
supports below metadata: _flavor, _max_claim_count, _dead_letter_queue,
_dead_letter_queue_messages_ttl and _enable_encrypt_messages.

In order to support the delayed queues, now add a metadata
``_default_message_delay``.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 201
   - 204

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 503


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name
  - _dead_letter_queue: _dead_letter_queue
  - _dead_letter_queue_messages_ttl: _dead_letter_queue_messages_ttl
  - _default_message_delay: _default_message_delay
  - _default_message_ttl: _default_message_ttl
  - _flavor: _flavor
  - _max_claim_count: _max_claim_count
  - _max_messages_post_size: _max_messages_post_size
  - _enable_encrypt_messages: _enable_encrypt_messages

Request Example
---------------

.. literalinclude:: samples/queue-create-request.json
   :language: javascript


This operation does not return a response body.


Update queue
============

.. rest_method:: PATCH /v2/queues/{queue_name}

Updates a queue.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 404
   - 409
   - 503


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

.. rest_method:: GET /v2/queues/{queue_name}

Shows details for a queue.

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

  - queue_name: queue_name

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - _max_messages_post_size: _max_messages_post_size
  - _default_message_delay: _default_message_delay_response
  - _default_message_ttl: _default_message_ttl
  - _max_claim_count: _max_claim_count_response
  - _dead_letter_queue: _dead_letter_queue_response
  - _dead_letter_queue_messages_ttl: _dead_letter_queue_messages_ttl_response
  - _enable_encrypt_messages: _enable_encrypt_messages

Response Example
----------------

.. literalinclude:: samples/queue-show-response.json
   :language: javascript


Delete queue
===============

.. rest_method:: DELETE /v2/queues/{queue_name}

Deletes the specified queue.

This operation immediately deletes a queue and all of its existing messages.

``queue_name`` is the name that you give to the queue. The name must not
exceed 64 bytes in length, and it is limited to US-ASCII letters, digits,
underscores, and hyphens.


Response codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 503


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

  - queue_name: queue_name

Response Example
----------------

.. literalinclude:: samples/queue-stats-response.json
   :language: javascript


Pre-signed queue
================

.. rest_method:: POST /v2/queues/{queue_name}/share

Create a pre-signed URL for a given queue.

.. note::

   In the case of pre-signed URLs, the queue cannot be created lazily. This
   is to prevent cases where queues are deleted and users still have a valid
   URL. This is not a big issues in cases where there's just 1 pool. However,
   if there's a deployment using more than 1 type of pool, the lazily created
   queue may end up in an undesired pool and it'd be possible for an attacker
   to try a DoS on that pool. Therefore, whenever a pre-signed URL is created,
   if a pool doesn't exist, it needs to be created.

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

  - queue_name: queue_name
  - paths: pre_signed_queue_paths
  - methods: pre_signed_queue_methods
  - expires: pre_signed_queue_expires

Request Example
---------------

.. literalinclude:: samples/queue-pre-signed-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - project: project_id
  - paths: pre_signed_queue_paths
  - methods: pre_signed_queue_methods
  - expires: pre_signed_queue_expires
  - signature: pre_signed_queue_signature

Response Example
----------------

.. literalinclude:: samples/queue-pre-signed-response.json
   :language: javascript


Purge queue
===========

.. rest_method:: POST /v2/queues/{queue_name}/purge

Purge particular resource of the queue.

.. note::

   Now Zaqar supports to purge "messages" and "subscriptions" resource from
   a queue.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 503


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name
  - resource_types: resource_types

Request Example
---------------

.. literalinclude:: samples/purge-queue-request.json
   :language: javascript

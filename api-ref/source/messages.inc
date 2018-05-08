===================
Messages (messages)
===================
Message is sent through a queue and exists until it is deleted by a recipient
or automatically by the system based on a TTL (time-to-live) value.

All message-related operations require Client-Id to be included in the headers.
This is to ensure that messages are not echoed back to the client that posted
them unless the client explicitly requests this.

Post Message
============

.. rest_method:: POST /v2/queues/{queue_name}/messages

Posts the message or messages for the specified queue.

This operation posts the specified message or messages.

You can submit up to 10 messages in a single request, but you must always
encapsulate the messages in a collection container (an array in JSON, even
for a single message - without the JSON array, you receive the "Invalid request
body" message). The resulting value of the Location header or response body
might be used to retrieve the created messages for further processing.

The client specifies only the body and TTL for the message. The server inserts
metadata, such as ID and age.

The response body contains a list of resource paths that correspond to each
message submitted in the request, in the order of the messages. If a
server-side error occurs during the processing of the submitted messages, a
partial list is returned, the partial attribute is set to true, and the client
tries to post the remaining messages again. If the server cannot enqueue any
messages, the server returns a ``503 Service Unavailable`` error message.

The ``body`` attribute specifies an arbitrary document that constitutes the
body of the message being sent.

.The following rules apply for the maximum size:

The maximum size of posted messages is the maximum size of the entire request
document (rather than the sum of the individual message body field values as
it was in earlier releases). On error, the client will now be notified of how
much it exceeded the limit.

The size is limited to 256 KB, including whitespace.

The document must be valid JSON. (The Message Queuing service validates it.)

The ``ttl`` attribute specifies how long the server waits before marking the
message as expired and removing it from the queue. The value of ``ttl`` must
be between 60 and 1209600 seconds (14 days). Note that the server might not
actually delete the message until its age has reached up to (ttl + 60) seconds,
to allow for flexibility in storage implementations.

The ``delay`` attribute specifies how long the message can be claimed.
The value of ``delay`` must be between 0 and 900 seconds (15 mins).

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 404
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name

Request Example
---------------

.. literalinclude:: samples/messages-post-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - resources: messages_resources

Response Example
----------------

.. literalinclude:: samples/messages-post-response.json
   :language: javascript


List Messages
=============

.. rest_method:: GET /v2/queues/{queue_name}/messages

List the messages in the specified queue.

A request to list messages when the queue is not found or when messages are
not found returns 204, instead of 200, because there was no information to
send back. Messages with malformed IDs or messages that are not found by ID
are ignored.

This operation gets the message or messages in the specified queue.

Message IDs and markers are opaque strings. Clients should make no assumptions
about their format or length. Furthermore, clients should assume that there is
no relationship between markers and message IDs (that is, one cannot be derived
from the other). This allows for a wide variety of storage driver
implementations.

Results are ordered by age, oldest message first.

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
  - marker: marker
  - limit: limit
  - echo: echo
  - include_claimed: include_claimed
  - include_delayed: include_delayed


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - messages: messages
  - links: links

Response Example
----------------

.. literalinclude:: samples/messages-list-response.json
   :language: javascript


Get A Set Of Messages
=====================

.. rest_method:: GET /v2/queues/{queue_name}/messages

Gets a specified set of messages from the specified queue.

This operation provides a more efficient way to query multiple messages
compared to using a series of individual ``GET`` s. Note that the list of IDs
cannot exceed 20. If a malformed ID or a nonexistent message ID is provided,
it is ignored, and the remaining messages are returned.

Unlike the Get Messages operation, a client's own messages are always returned
in this operation. If you use the ids parameter, the echo parameter is not used
and is ignored if it is specified.

The message attributes are defined as follows: ``href`` is an opaque relative
URI that the client can use to uniquely identify a message resource and
interact with it. ``ttl`` is the TTL that was set on the message when it was
posted. The message expires after (ttl - age) seconds. ``age`` is the number
of seconds relative to the server's clock. ``body`` is the arbitrary document
that was submitted with the original request to post the message. ``checksum``
is the hash digest of the ``body``, default algorithm is MD5.



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
  - ids: ids


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - messages: messages

Response Example
----------------

.. literalinclude:: samples/messages-get-byids-response.json
   :language: javascript


Delete A Set Of Messages
========================

.. rest_method:: DELETE /v2/queues/{queue_name}/messages

Provides a bulk delete for messages.

This operation immediately deletes the specified messages. If any of the
message IDs are malformed or non-existent, they are ignored. The remaining
valid messages IDs are deleted. Please note that users should input either
``ids`` or ``pop`` parameter, otherwise this API will delete nothing. If
``pop`` is provided, the value must be at least 1 and may not be greater than
``max_messages_per_claim_or_pop`` in conf. If ``ids`` is provided, it should
contain at least one id and not greater than ``max_messages_per_page`` in conf.



Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200
   - 204


.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 404
   - 503


Request Parameters
------------------

This operation does not accept a request body.

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name
  - ids: ids
  - pop: pop


Response Example
----------------

This operation only returns a response body when the ``pop`` query parameter
is used.

.. literalinclude:: samples/messages-delete-bypop-response.json
   :language: javascript


Get A Specific Message
======================

.. rest_method:: GET /v2/queues/{queue_name}/messages/{message_id}

Gets the specified message from the specified queue.

This operation gets the specified message from the specified queue.

If either the message ID is malformed or nonexistent, no message is returned.

Message fields are defined as follows: ``href`` is an opaque relative URI that
the client can use to uniquely identify a message resource and interact with
it. ``ttl`` is the TTL that was set on the message when it was posted. The
message expires after (ttl - age) seconds. ``age`` is the number of seconds
relative to the server's clock. ``body`` is the arbitrary document that was
submitted with the original request to post the message. ``checksum`` is the
hash digest of the ``body``, default algorithm is MD5.



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
  - message_id: message_id

Response Example
----------------

.. literalinclude:: samples/messages-get-response.json
   :language: javascript


Delete A Specific Message
=========================

.. rest_method:: DELETE /v2/queues/{queue_name}/messages/{message_id}

Deletes the specified message from the specified queue.

This operation immediately deletes the specified message.

The ``claim_id`` parameter specifies that the message is deleted only if it
has the specified claim ID and that claim has not expired. This specification
is useful for ensuring only one worker processes any given message. When a
worker's claim expires before it can delete a message that it has processed,
the worker must roll back any actions it took based on that message because
another worker can now claim and process the same message.

If you do not specify ``claim_id``, but the message is claimed, the operation
fails. You can only delete claimed messages by providing an appropriate
``claim_id``.



Response codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 404
   - 503

Request
-------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name
  - message_id: message_id

This operation does not accept a request body and does not return a response
body.


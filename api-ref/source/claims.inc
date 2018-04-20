===============
Claims (claims)
===============
Claim is a mechanism to mark messages so that other workers will not process
the same message.

Claim messages
==============

.. rest_method:: POST /v2/queues/{queue_name}/claims

Claims a set of messages from the specified queue.

This operation claims a set of messages (up to the value of the ``limit``
parameter) from oldest to newest and skips any messages that are already
claimed. If no unclaimed messages are available, the API returns a
``204 No Content`` message.

When a client (worker) finishes processing a message, it should delete the
message before the claim expires to ensure that the message is processed only
once. As part of the delete operation, workers should specify the claim ID
(which is best done by simply using the provided href). If workers perform
these actions, then if a claim simply expires, the server can return an error
and notify the worker of the race condition. This action gives the worker a
chance to roll back its own processing of the given message because another
worker can claim the message and process it.

The age given for a claim is relative to the server's clock. The claim's age
is useful for determining how quickly messages are getting processed and
whether a given message's claim is about to expire.

When a claim expires, it is released. If the original worker failed to process
the message, another client worker can then claim the message.

Note that claim creation is best-effort, meaning the worker may claim and
return less than the requested number of messages.

The ``ttl`` attribute specifies how long the server waits before releasing
the claim. The ttl value must be between 60 and 43200 seconds (12 hours).
You must include a value for this attribute in your request.

The ``grace`` attribute specifies the message grace period in seconds. The
value of ``grace`` value must be between 60 and 43200 seconds (12 hours).
You must include a value for this attribute in your request. To deal with
workers that have stopped responding (for up to 1209600 seconds or 14 days,
including claim lifetime), the server extends the lifetime of claimed messages
to be at least as long as the lifetime of the claim itself, plus the specified
grace period. If a claimed message would normally live longer than the claim's
live period, its expiration is not adjusted.



Response codes
--------------

.. rest_status_code:: success status.yaml

   - 201
   - 204

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 503

Request Parameters
------------------


.. rest_parameters:: parameters.yaml

  - queue_name: queue_name
  - limit: claim_limit
  - ttl: claim_ttl
  - grace: claim_grace

**Example Claim Messages: JSON request**


.. literalinclude:: samples/claim_messages_request.json
   :language: javascript



Response Parameters
-------------------

**Example Claim Messages: JSON response**


.. literalinclude:: samples/claim_messages_response.json
   :language: javascript



Query Claim
===========

.. rest_method:: GET /v2/queues/{queue_name}/claims/{claim_id}

Queries the specified claim for the specified queue.

This operation queries the specified claim for the specified queue. Claims
with malformed IDs or claims that are not found by ID are ignored.



Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name
  - claim_id: claim_id

Response Parameters
-------------------

**Example Query Claim: JSON response**


.. literalinclude:: samples/claim_query_response.json
   :language: javascript



Update(Renew) Claim
===================

.. rest_method:: PATCH /v2/queues/{queue_name}/claims/{claim_id}

Updates the specified claim for the specified queue.

This operation updates the specified claim for the specified queue. Claims
with malformed IDs or claims that are not found by ID are ignored.

Clients should periodically renew claims during long-running batches of work
to avoid losing a claim while processing a message. The client can renew a
claim by issuing a ``PATCH`` command to a specific claim resource and
including a new TTL for the claim (which can be different from the original
TTL). The server resets the age of the claim and applies the new TTL.



Response codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 503

Request Parameters
------------------


.. rest_parameters:: parameters.yaml

  - queue_name: queue_name
  - claim_id: claim_id
  - ttl: claim_ttl
  - grace: claim_grace

**Example Update Claim: JSON request**


.. literalinclude:: samples/claim_update_request.json
   :language: javascript


This operation does not return a response body.


Delete(Release) Claim
=====================

.. rest_method:: DELETE /v2/queues/{queue_name}/claims/{claim_id}

Releases the specified claim for the specified queue.

This operation immediately releases a claim, making any remaining, undeleted)
messages that are associated with the claim available to other workers. Claims
with malformed IDs or claims that are not found by ID are ignored.

This operation is useful when a worker is performing a graceful shutdown,
fails to process one or more messages, or is taking longer than expected to
process messages, and wants to make the remainder of the messages available
to other workers.



Response codes
--------------

.. rest_status_code:: success status.yaml

   - 204


.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 503

Request Parameters
------------------


.. rest_parameters:: parameters.yaml

  - queue_name: queue_name
  - claim_id: claim_id


This operation does not accept a request body and does not return a response
body.

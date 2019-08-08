Common Headers
==============

Each request to the Message Queuing API must include certain standard
and extended HTTP headers (as shown in the following table). These
headers provide host, agent, authentication, and other pertinent
information to the server. The following table provides the common
headers used by the API.

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Header
     - Description
   * - Host
     - Host name of the API
   * - Date
     - Current date and time
   * - Accept
     - Media type to use. Initially, only ``application/json`` is
       supported. **Note: The "Accept" header is required.**
   * - Accept-Encoding
     - Specifies that the agent accepts gzip-encoded response bodies
   * - Content-Type
     - ``application/json``
   * - Content-Length
     - For ``POST`` or ``PUT`` requests, the length in bytes of the
       message document being submitted
   * - X-Auth-Token
     - Authorization token
   * - X-Project-Id
     - An ID for a project to which the value of X-Auth-Token grants
       access. Queues are created under this project. The project ID
       is the same as the account ID (also sometimes called tenant ID).
   * - Client-ID
     - A UUID for each client instance. The UUID must be submitted in
       its canonical form (for example, 3381af92-2b9e-11e3-b191-71861300734c).
       The client generates the Client-ID once. Client-ID persists
       between restarts of the client so the client should
       reuse that same Client-ID.

**Note: All message-related operations require the use of "Client-ID" in
the headers to ensure that messages are not echoed back to the client that
posted them, unless the client explicitly requests this.**

Working with the Message Queuing API
====================================

This chapter contains a simple exercise with some basic Message Queuing
requests that you will commonly use. Example requests are provided in
cURL, followed by the response.

For a complete list of operations available for Message Queuing, see :doc:`getting_started`
Each operation is fully described in the `Message Queuing API v2
Reference <https://docs.openstack.org/api-ref/message/>`_.

Create Queue
------------

The Create Queue operation creates a queue in the region of your choice.

The body of the PUT request is empty.

The template is as follows:

.. code:: rest

    PUT {endpoint}/queues/{queue_name}

The ``queue_name`` parameter specifies the name to give the queue. The
name *must not* exceed 64 bytes in length and is limited to US-ASCII
letters, digits, underscores, and hyphens.

Following are examples of a Create Queue request and response:

.. code-block:: bash

    curl -i -X PUT https://queues.api.openstack.org/v2/queues/samplequeue \
    -H "X-Auth-Token: " \
    -H "Accept: application/json" \
    -H "X-Project-Id: "

.. code:: rest

    HTTP/1.1 201 Created
    Content-Length: 0
    Location: /v2/queues/samplequeue

Post Message
------------

The Post Message operation inserts one or more messages in a queue.

You can submit up to 10 messages in a single request, but you must
encapsulate them in a collection container (an array in JSON, even for a
single message - without the JSON array, you receive an "Invalid body
request" error message). You can use the resulting value of the location
header or response body to retrieve the created messages for further
processing if needed.

The template is as follows:

.. code:: rest

    POST {endpoint}/queues/{queue_name}/messages

The client specifies only the body and ttl attributes for the message.
Metadata, such as id and age, is added.

The response body contains a list of resource paths that correspond to
each message submitted in the request, in the same order as they were
submitted.

If a server-side error occurs during the processing of the submitted
messages, a partial list is returned. The ``partial`` attribute is set
to ``true``, and the client tries to post the remaining messages again.

    **Important**

    The ``partial`` attribute has been deprecated in the v1.0 API and is
    not available in the v1.1 API. Drivers are now required to operate
    in a transactional manner. In other words, either all messages must
    be posted, or none of them.

The ``body`` attribute specifies an arbitrary document that constitutes
the body of the message being sent.

The following rules apply for the maximum size:

-  The size is limited to 256 KB for the entire request body (as-is),
   including whitespace.

-  The maximum size of posted messages is the maximum size of the entire
   request document (rather than the sum of the individual message
   ``body`` field values as it was earlier releases). On error, the
   client is notified of by how much the request exceeded the limit.

The document *must* be valid JSON. (The Message Queuing service
validates it.)

The ``ttl`` attribute specifies the lifetime of the message. When the
lifetime expires, the server deletes the message and removes it from the
queue. Valid values are 60 through 1209600 seconds (14 days).

    **Note**

    The server might not actually delete the message until its age
    reaches (ttl + 60) seconds. So there might be a delay of 60 seconds
    after the message expires before it is deleted.

The following are examples of a Post Message request and response:

.. code:: bash

    curl -i -X POST https://queues.api.openstack.org/v1/queues/samplequeue/messages -d \
    '[{"ttl": 300,"body": {"event": "BackupStarted"}},{"ttl": 60,"body": {"play": "hockey"}}]' \
    -H "Content-type: application/json" \
    -H "Client-ID: e58668fc-26eb-11e3-8270-5b3128d43830" \
    -H "X-Auth-Token: " \
    -H "Accept: application/json" \
    -H "X-Project-Id: "

.. code:: rest

    HTTP/1.1 201 Created
    Content-Length: 153
    Content-Type: application/json; charset=utf-8
    Location: /v1/queues/samplequeue/messages?ids=51ca00a0c508f154c912b85c,51ca00a0c508f154c912b85d

    {"partial": false, "resources": ["/v1/queues/samplequeue/messages/51ca00a0c508f154c912b85c", "/v1/queues/samplequeue/messages/51ca00a0c508f154c912b85d"]}

Claim Messages
--------------

The Claim Messages operation claims a set of messages (up to the value
of the ``limit`` parameter) from oldest to newest and skips any messages
that are already claimed. If there are no messages available to claim,
the Message Queuing service returns an HTTP ``204 No Content`` response
code.

The template is as follows:

.. code-block:: rest

    POST {endpoint}/queues/{queue_name}/claims{?limit}
    Content-Type: application/json

    {
        "ttl": {claim_ttl},
        "grace": {message_grace}
    }

The client (worker) needs to delete the message when it has finished
processing it. The client deletes the message before the claim expires
to ensure that the message is processed only once. If a client needs
more time, the Cloud Service provides the Update Claim operation to make
changes. See the Message Queuing API v1 Reference for a description of
this operation. As part of the delete operation, workers specify the
claim ID (which is best done by simply using the provided href). If
workers perform these actions, then if a claim simply expires, the
server can return an error and notify the worker of a possible race
condition. This action gives the worker a chance to roll back its own
processing of the given message because another worker can claim the
message and process it.

The age given for a claim is relative to the server's clock. The claim's
age is useful for determining how quickly messages are getting processed
and whether a given message's claim is about to expire.

When a claim expires, it is released back to the queue for other workers
to claim. (If the original worker failed to process the message, another
client worker can then claim the message.)

The ``limit`` parameter specifies the number of messages to claim. The
``limit`` parameter is configurable. The default is 20. Messages are
claimed based on the number of messages available. The server might
claim and return less than the requested number of messages.

The ``ttl`` attribute specifies the lifetime of the claim. While
messages are claimed, they are not available to other workers. The value
must be between 60 and 43200 seconds (12 hours).

The ``grace`` attribute specifies the message grace period in seconds.
Valid values are between 60 and 43200 seconds (12 hours). To deal with
workers that have stopped responding (for up to 1209600 seconds or 14
days, including claim lifetime), the server extends the lifetime of
claimed messages to be at least as long as the lifetime of the claim
itself, plus the specified grace period. If a claimed message normally
lives longer than the grace period, its expiration is not adjusted. it

Following are examples of a Claim Messages request and response:

.. code:: bash

    curl -i -X POST https://queues.api.openstack.org/v1/queues/samplequeue/claims -d \
    '{"ttl": 300,"grace":300}' \
    -H "Content-type: application/json" \
    -H "Client-ID: e58668fc-26eb-11e3-8270-5b3128d43830" \
    -H "X-Auth-Token: " \
    -H "Accept: application/json" \
    -H "X-Project-Id: "

.. code-block:: rest

    HTTP/1.1 201 OK
    Content-Length: 164
    Content-Type: application/json; charset=utf-8
    Location: /v1/queues/samplequeue/claims/51ca011c821e7250f344efd6
    X-Project-Id:

    [
      {
        "body": {
          "event": "BackupStarted"
        },
        "age": 124,
        "href": "\/v1\/queues\/samplequeue\/messages\/51ca00a0c508f154c912b85c?claim_id=51ca011c821e7250f344efd6",
        "ttl": 300
      }
    ]

Delete Message with Claim ID
----------------------------

The Delete Message operations deletes messages.

The template is as follows:

.. code:: rest

    DELETE {endpoint}/queues/{queue_name}/messages/{message_id}{?claim_id}

The ``message_id`` parameter specifies the message to delete.

The ``claim_id`` parameter specifies that the message is deleted only if
it has the specified claim ID and that claim has not expired. This
specification is useful for ensuring that only one worker processes any
given message. When a worker's claim expires before it deletes a message
that it has processed, the worker must roll back any actions it took
based on that message because another worker can now claim and process
the same message.

Following are examples of a Delete Message request and response:

.. code:: bash

    curl -i -X DELETE https://queues.api.openstack.org/v1/queues/samplequeue/messages/51ca00a0c508f154c912b85c?claim_id=51ca011c821e7250f344efd6 \
    -H "Content-type: application/json" \
    -H "X-Auth-Token: " \
    -H "Client-ID: e58668fc-26eb-11e3-8270-5b3128d43830" \
    -H "Accept: application/json" \
    -H "X-Project-Id: "

.. code:: rest

    HTTP/1.1 204 No Content

Release Claim
-------------

The Release Claim operation immediately releases a claim, making any
remaining, undeleted) messages associated with the claim available to
other workers.

The template is as follows:

.. code:: rest

    DELETE {endpoint}/queues/{queue_name}/claims/{claim_id}

This operation is useful when a worker is performing a graceful
shutdown, fails to process one or more messages, or is taking longer
than expected to process messages and wants to make the remainder of the
messages available to other workers.

Following are examples of a Release Claim request and response:

.. code:: bash

    curl -i -X DELETE https://queues.api.openstack.org/v1/queues/samplequeue/claims/51ca011c821e7250f344efd6 \
    -H "Content-type: application/json" \
    -H "X-Auth-Token: " \
    -H "Client-ID: e58668fc-26eb-11e3-8270-5b3128d43830"  \
    -H "Accept: application/json" \
    -H "X-Project-Id: "

.. code:: rest

    HTTP/1.1 204 No Content

Delete Queue
------------

The Delete Queue operation immediately deletes a queue and all of its
existing messages.

The template is as follows:

.. code:: rest

    DELETE {endpoint}/queues/{queue_name}

Following are examples of a Delete Queue request and response:

.. code:: bash

    curl -i -X DELETE https://queues.api.openstack.org/v1/queues/samplequeue \
    -H "Content-type: application/json" \
    -H "X-Auth-Token: " \
    -H "Accept: application/json" \
    -H "X-Project-Id: "

.. code:: rest

    HTTP/1.1 204 No Content

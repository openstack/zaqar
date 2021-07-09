============================
Subscriptions(subscriptions)
============================
Subscriptions are relationships between queue/topic and the targeted
subscribers. After created subscriptions for a particular subscriber, like an
email or a webhook, then when new messages posted to the queue, the subscriber
will be notified automatically.

List Subscriptions
==================

.. rest_method:: GET /v2/queues/{queue_name}/subscriptions

Lists a queue's subscriptions.

This operation lists subscriptions for a queue. The subscriptions are sorted
alphabetically by name.


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


Query Parameters
~~~~~~~~~~~~~~~~

.. rest_parameters:: parameters.yaml

  - limit: limit
  - marker: marker


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - subscriptions: subscriptions
  - links: links


Response Example
----------------

.. literalinclude:: samples/subscriptions-list-response.json
   :language: javascript


Create Subscription
===================

.. rest_method:: POST /v2/queues/{queue_name}/subscriptions

Creates a subscription.

This operation creates a new subscription.


Response codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 503


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name
  - subscriber: subscriber
  - ttl: subscription_ttl
  - options: subscription_options


Request Example
---------------

.. literalinclude:: samples/subscription-create-request-http.json
   :language: javascript

.. literalinclude:: samples/subscription-create-request-mail.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - subscription_id: subscription_id


Response Example
----------------

.. literalinclude:: samples/subscription-create-response.json
   :language: javascript


Update Subscription
===================

.. rest_method:: PATCH /v2/queues/{queue_name}/subscriptions/{subscription_id}

Updates a subscription.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 204

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
  - subscription_id: subscription_id_path
  - subscriber: subscriber
  - ttl: subscription_ttl
  - options: subscription_options


Request Example
---------------

.. literalinclude:: samples/subscription-update-request.json
   :language: javascript


This operation does not return a response body.


Show Subscription Details
=========================

.. rest_method:: GET /v2/queues/{queue_name}/subscriptions/{subscription_id}

Shows details for a subscription.

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
  - subscription_id: subscription_id_path


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - age: subscription_age
  - id: subscription_id
  - subscriber: subscriber
  - source: subscription_source
  - ttl: subscription_ttl
  - options: subscription_options


Response Example
----------------

.. literalinclude:: samples/subscription-show-response.json
   :language: javascript


Delete Subscription
===================

.. rest_method:: DELETE /v2/queues/{queue_name}/subscriptions/{subscription_id}

Deletes the specified subscription.


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
  - subscription_id: subscription_id_path


This operation does not accept a request body and does not return a response
body.


Confirm Subscription
====================

.. rest_method:: POST /v2/queues/{queue_name}/subscriptions/{subscription_id}/confirm

Confirm a subscription.

This operation can confirm or cancel a subscription.


Response codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 503


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - queue_name: queue_name
  - subscription_id: subscription_id_path
  - confirmed: confirmed


Request Example
---------------

.. literalinclude:: samples/subscription-confirm-request.json
   :language: javascript


This operation does not return a response body.
